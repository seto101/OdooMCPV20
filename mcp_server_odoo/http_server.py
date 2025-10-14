"""HTTP server implementation with FastAPI for N8N, ChatGPT, and web agents."""

from datetime import timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, RedirectResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog
import uvicorn

from .config import get_settings, Settings
from .auth import AuthManager
from .odoo_client import OdooClient
from .cache import CacheManager
from .tools import get_tools, handle_tool_call
from .mcp_tools import mcp
from .oauth import oauth_manager

logger = structlog.get_logger()


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"


class OAuthTokenRequest(BaseModel):
    """OAuth token request model."""
    grant_type: str
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    refresh_token: Optional[str] = None


class ToolCallRequest(BaseModel):
    """Tool call request model."""
    tool: str
    arguments: dict


class ToolListResponse(BaseModel):
    """Tool list response model."""
    tools: list


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    settings = get_settings()
    
    # Create MCP ASGI app with internal path="/" 
    # When mounted at "/mcp", the endpoint will be "/mcp/"
    mcp_asgi_app = mcp.http_app(path="/")
    
    # Create FastAPI app with MCP lifespan (CRITICAL for MCP to work)
    app = FastAPI(
        title="Odoo MCP Server",
        description="Enhanced MCP server for Odoo with API authentication",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=mcp_asgi_app.lifespan
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    auth_manager = AuthManager(settings, oauth_manager=oauth_manager)
    cache_manager = CacheManager(ttl=settings.cache_ttl)
    odoo_client = OdooClient(settings, cache_manager)
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "Odoo MCP Server",
            "version": "2.0.0",
            "status": "running",
            "endpoints": {
                "mcp_streamable": "/mcp (POST - for N8N MCP node)",
                "docs": "/docs",
                "tools": "/tools",
                "call_tool": "/call_tool",
                "login": "/login",
                "webhook_n8n": "/webhook/n8n"
            },
            "n8n_connection": {
                "transport": "HTTP Streamable",
                "endpoint": "/mcp",
                "authentication": "Bearer token (use API_KEYS from env or JWT from /login)"
            }
        }
    
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        try:
            uid = odoo_client.authenticate()
            return {
                "status": "healthy",
                "odoo_connected": True,
                "odoo_uid": uid
            }
        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "unhealthy",
                    "odoo_connected": False,
                    "error": str(e)
                }
            )
    
    @app.post("/login", response_model=TokenResponse)
    async def login(request: LoginRequest):
        """
        Login endpoint to get JWT token.
        
        Validates credentials against Odoo credentials configured in environment.
        For production use, consider implementing a proper user database.
        """
        logger.info("login_attempt", username=request.username)
        
        if not settings.odoo_username or not settings.odoo_password:
            logger.error("login_failed_no_credentials_configured")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Server authentication not configured. Set ODOO_USERNAME and ODOO_PASSWORD."
            )
        
        if request.username != settings.odoo_username or request.password != settings.odoo_password:
            logger.warning("login_failed_invalid_credentials", username=request.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        try:
            uid = odoo_client.authenticate()
            logger.info("odoo_authentication_verified", uid=uid)
        except Exception as e:
            logger.error("odoo_authentication_failed_during_login", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed: unable to verify credentials with Odoo"
            )
        
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = auth_manager.create_access_token(
            data={"sub": request.username, "odoo_uid": uid},
            expires_delta=access_token_expires
        )
        
        logger.info("login_successful", username=request.username, odoo_uid=uid)
        
        return TokenResponse(access_token=access_token)
    
    @app.get("/oauth/authorize")
    async def oauth_authorize(
        response_type: str,
        client_id: str,
        redirect_uri: str,
        state: Optional[str] = None,
        scope: Optional[str] = None
    ):
        """
        OAuth 2.0 authorization endpoint.
        
        For ChatGPT and other OAuth clients.
        This is a simplified flow - in production, show a consent screen.
        """
        logger.info(
            "oauth_authorize_request",
            client_id=client_id,
            redirect_uri=redirect_uri,
            response_type=response_type
        )
        
        if response_type != "code":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only 'code' response_type is supported"
            )
        
        try:
            # Generate authorization code
            code = oauth_manager.generate_authorization_code(
                client_id=client_id,
                redirect_uri=redirect_uri,
                state=state,
                scope=scope
            )
            
            # Redirect back to client with code
            redirect_url = f"{redirect_uri}?code={code}"
            if state:
                redirect_url += f"&state={state}"
            
            logger.info("oauth_authorize_success", redirect_uri=redirect_uri)
            
            return RedirectResponse(url=redirect_url)
            
        except ValueError as e:
            logger.error("oauth_authorize_error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    @app.post("/oauth/token")
    async def oauth_token(request: OAuthTokenRequest):
        """
        OAuth 2.0 token endpoint.
        
        Exchange authorization code for access token or refresh an existing token.
        """
        logger.info("oauth_token_request", grant_type=request.grant_type)
        
        try:
            if request.grant_type == "authorization_code":
                # Exchange code for token
                if not all([request.code, request.client_id, request.client_secret, request.redirect_uri]):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Missing required parameters for authorization_code grant"
                    )
                
                # Type assertions after validation
                assert request.code is not None
                assert request.client_id is not None
                assert request.client_secret is not None
                assert request.redirect_uri is not None
                
                token_data = oauth_manager.exchange_code_for_token(
                    code=request.code,
                    client_id=request.client_id,
                    client_secret=request.client_secret,
                    redirect_uri=request.redirect_uri
                )
                
                logger.info("oauth_token_issued", client_id=request.client_id)
                return token_data
                
            elif request.grant_type == "refresh_token":
                # Refresh token
                if not all([request.refresh_token, request.client_id, request.client_secret]):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Missing required parameters for refresh_token grant"
                    )
                
                # Type assertions after validation
                assert request.refresh_token is not None
                assert request.client_id is not None
                assert request.client_secret is not None
                
                token_data = oauth_manager.refresh_access_token(
                    refresh_token=request.refresh_token,
                    client_id=request.client_id,
                    client_secret=request.client_secret
                )
                
                logger.info("oauth_token_refreshed", client_id=request.client_id)
                return token_data
                
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported grant_type: {request.grant_type}"
                )
                
        except ValueError as e:
            logger.error("oauth_token_error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    @app.get("/oauth/credentials")
    async def oauth_credentials():
        """
        Get OAuth client credentials for setup.
        
        This endpoint is for initial configuration only.
        In production, protect this endpoint or remove it.
        """
        credentials = oauth_manager.get_client_credentials()
        server_url = settings.get_server_url()
        
        logger.info("oauth_credentials_retrieved", server_url=server_url)
        
        return {
            **credentials,
            "authorization_url": f"{server_url}/oauth/authorize",
            "token_url": f"{server_url}/oauth/token",
            "scopes": ["odoo:read", "odoo:write"],
            "note": "Use these credentials to configure ChatGPT or other OAuth clients"
        }
    
    @app.get("/tools", response_model=ToolListResponse)
    async def list_tools(auth: dict = Depends(auth_manager.verify_request)):
        """
        List all available MCP tools.
        
        Requires authentication via API key or JWT token.
        """
        logger.info("tools_listed", auth_type=auth.get("auth_type"))
        
        tools = get_tools()
        
        return ToolListResponse(
            tools=[
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
                for tool in tools
            ]
        )
    
    @app.post("/call_tool")
    async def call_tool(
        request: ToolCallRequest,
        auth: dict = Depends(auth_manager.verify_request)
    ):
        """
        Call an MCP tool.
        
        Requires authentication via API key or JWT token.
        """
        logger.info(
            "tool_call_requested",
            tool=request.tool,
            auth_type=auth.get("auth_type")
        )
        
        try:
            result = await handle_tool_call(
                request.tool,
                request.arguments,
                odoo_client
            )
            
            return {
                "success": True,
                "result": result[0].text if result else None
            }
            
        except Exception as e:
            logger.error("tool_call_error", tool=request.tool, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @app.post("/webhook/n8n")
    async def n8n_webhook(
        request: ToolCallRequest,
        auth: dict = Depends(auth_manager.verify_request)
    ):
        """
        N8N-specific webhook endpoint.
        
        Compatible with N8N HTTP Request node.
        """
        logger.info("n8n_webhook_called", tool=request.tool)
        
        try:
            result = await handle_tool_call(
                request.tool,
                request.arguments,
                odoo_client
            )
            
            return JSONResponse(
                content={
                    "success": True,
                    "data": result[0].text if result else None,
                    "webhook": "n8n"
                }
            )
            
        except Exception as e:
            logger.error("n8n_webhook_error", tool=request.tool, error=str(e))
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "error": str(e),
                    "webhook": "n8n"
                }
            )
    
    @app.on_event("startup")
    async def startup_event():
        """Run on application startup."""
        logger.info("http_server_starting", port=settings.port, host=settings.host)
        
        if settings.odoo_url and settings.odoo_db and settings.odoo_username:
            try:
                uid = odoo_client.authenticate()
                logger.info("odoo_authenticated", uid=uid)
            except Exception as e:
                logger.warning("odoo_authentication_failed", error=str(e))
        else:
            logger.warning("odoo_credentials_not_configured", message="Set ODOO_URL, ODOO_DB, ODOO_USERNAME, and ODOO_PASSWORD to use Odoo features")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Run on application shutdown."""
        logger.info("http_server_shutting_down")
    
    # Add explicit handler for /mcp without trailing slash
    # Redirect to /mcp/ with 308 (Permanent Redirect that preserves method)
    @app.api_route("/mcp", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"], include_in_schema=False)
    async def mcp_redirect():
        """Redirect /mcp to /mcp/ preserving the request method."""
        return RedirectResponse(url="/mcp/", status_code=308)
    
    # Mount MCP app AFTER explicit redirect route
    # The MCP endpoint will be at /mcp/
    app.mount("/mcp", mcp_asgi_app)
    logger.info("mcp_http_endpoint_ready", paths=["/mcp (redirects to /mcp/)", "/mcp/"])
    
    return app


def run_http_server():
    """Run the HTTP server."""
    settings = get_settings()
    
    app = create_app()
    
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    run_http_server()
