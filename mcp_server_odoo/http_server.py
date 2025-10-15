"""HTTP server implementation with FastAPI for N8N, ChatGPT, and web agents."""

from datetime import timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, status, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, RedirectResponse, HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
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
    basic_security = HTTPBasic(auto_error=False)
    
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
        
        Shows consent page for OAuth clients like ChatGPT.
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
            # Obtener información del cliente
            client = oauth_manager.get_client(client_id)
            if not client:
                raise ValueError("Invalid client_id")
            
            client_name = client.get("client_name", "Unknown Application")
            requested_scope = scope or client.get("scope", "odoo:read odoo:write")
            
            # Mostrar página de consentimiento
            consent_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Authorize Access</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
                           display: flex; justify-content: center; align-items: center; 
                           min-height: 100vh; margin: 0; background: #f5f5f5; }}
                    .container {{ background: white; padding: 2rem; border-radius: 8px; 
                                 box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 400px; }}
                    h1 {{ margin: 0 0 1rem; color: #333; }}
                    .client-name {{ color: #0066cc; font-weight: 600; }}
                    .scopes {{ background: #f8f9fa; padding: 1rem; border-radius: 4px; margin: 1rem 0; }}
                    .scope-item {{ margin: 0.5rem 0; }}
                    button {{ width: 100%; padding: 0.75rem; border: none; border-radius: 4px; 
                             font-size: 1rem; cursor: pointer; font-weight: 600; }}
                    .authorize {{ background: #0066cc; color: white; margin-bottom: 0.5rem; }}
                    .authorize:hover {{ background: #0052a3; }}
                    .deny {{ background: #e0e0e0; color: #666; }}
                    .deny:hover {{ background: #d0d0d0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Authorize Access</h1>
                    <p><span class="client-name">{client_name}</span> wants to access your Odoo data.</p>
                    
                    <div class="scopes">
                        <strong>Permissions requested:</strong>
                        <div class="scope-item">✓ Read Odoo data</div>
                        <div class="scope-item">✓ Write Odoo data</div>
                    </div>
                    
                    <form method="post" action="/oauth/authorize/approve">
                        <input type="hidden" name="client_id" value="{client_id}">
                        <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                        <input type="hidden" name="state" value="{state or ''}">
                        <input type="hidden" name="scope" value="{requested_scope}">
                        <button type="submit" class="authorize">Authorize</button>
                    </form>
                    
                    <button class="deny" onclick="window.location.href='{redirect_uri}?error=access_denied&state={state or ''}'">
                        Deny
                    </button>
                </div>
            </body>
            </html>
            """
            
            return HTMLResponse(content=consent_html)
            
        except ValueError as e:
            logger.error("oauth_authorize_error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    @app.post("/oauth/authorize/approve")
    async def oauth_authorize_approve(
        client_id: str = Form(...),
        redirect_uri: str = Form(...),
        state: Optional[str] = Form(None),
        scope: Optional[str] = Form(None)
    ):
        """
        Handle OAuth consent approval.
        """
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
            
            logger.info("oauth_consent_approved", client_id=client_id)
            
            return RedirectResponse(url=redirect_url, status_code=303)
            
        except ValueError as e:
            logger.error("oauth_approve_error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    @app.post("/oauth/token")
    async def oauth_token(
        grant_type: str = Form(...),
        code: Optional[str] = Form(None),
        redirect_uri: Optional[str] = Form(None),
        client_id: Optional[str] = Form(None),
        client_secret: Optional[str] = Form(None),
        refresh_token: Optional[str] = Form(None),
        basic_credentials: Optional[HTTPBasicCredentials] = Depends(basic_security)
    ):
        """
        OAuth 2.0 token endpoint (RFC 6749).
        
        Accepts application/x-www-form-urlencoded as per OAuth 2.0 spec.
        Supports HTTP Basic Auth for client credentials (preferred by ChatGPT) or form parameters.
        Exchange authorization code for access token or refresh an existing token.
        """
        # Extract client credentials from HTTP Basic Auth if present, otherwise use form data
        final_client_id = client_id
        final_client_secret = client_secret
        
        if basic_credentials:
            final_client_id = basic_credentials.username
            final_client_secret = basic_credentials.password
            logger.info("oauth_token_request_basic_auth", grant_type=grant_type, client_id=final_client_id)
        else:
            logger.info("oauth_token_request_form", grant_type=grant_type, client_id=final_client_id)
        
        try:
            if grant_type == "authorization_code":
                # Exchange code for token
                if not all([code, final_client_id, redirect_uri]):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Missing required parameters for authorization_code grant"
                    )
                
                # Type assertions after validation
                assert code is not None
                assert final_client_id is not None
                assert redirect_uri is not None
                
                # Obtener cliente para verificar si requiere secret
                client = oauth_manager.get_client(final_client_id)
                if not client:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid client_id"
                    )
                
                # Validar client_secret solo para clientes confidenciales
                if client.get("token_endpoint_auth_method") != "none":
                    if not final_client_secret:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="client_secret required for confidential clients"
                        )
                
                token_data = oauth_manager.exchange_code_for_token(
                    code=code,
                    client_id=final_client_id,
                    client_secret=final_client_secret,
                    redirect_uri=redirect_uri
                )
                
                logger.info("oauth_token_issued", client_id=final_client_id)
                return token_data
                
            elif grant_type == "refresh_token":
                # Refresh token
                if not all([refresh_token, final_client_id]):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Missing required parameters for refresh_token grant"
                    )
                
                # Type assertions after validation
                assert refresh_token is not None
                assert final_client_id is not None
                
                # Obtener cliente para verificar si requiere secret
                client = oauth_manager.get_client(final_client_id)
                if not client:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid client_id"
                    )
                
                # Validar client_secret solo para clientes confidenciales
                if client.get("token_endpoint_auth_method") != "none":
                    if not final_client_secret:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="client_secret required for confidential clients"
                        )
                
                token_data = oauth_manager.refresh_access_token(
                    refresh_token=refresh_token,
                    client_id=final_client_id,
                    client_secret=final_client_secret
                )
                
                logger.info("oauth_token_refreshed", client_id=final_client_id)
                return token_data
                
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported grant_type: {grant_type}"
                )
                
        except ValueError as e:
            logger.error("oauth_token_error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    @app.get("/.well-known/oauth-authorization-server")
    async def oauth_authorization_server_metadata():
        """
        OAuth 2.0 Authorization Server Metadata (RFC 8414).
        
        Provides discovery information for OAuth clients like ChatGPT.
        """
        server_url = settings.get_server_url()
        
        return {
            "issuer": server_url,
            "authorization_endpoint": f"{server_url}/oauth/authorize",
            "token_endpoint": f"{server_url}/oauth/token",
            "registration_endpoint": f"{server_url}/oauth/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "token_endpoint_auth_methods_supported": ["none", "client_secret_basic", "client_secret_post"],
            "scopes_supported": ["odoo:read", "odoo:write"],
            "code_challenge_methods_supported": ["plain", "S256"]
        }
    
    @app.get("/.well-known/oauth-protected-resource")
    async def oauth_protected_resource_metadata():
        """
        OAuth 2.0 Protected Resource Metadata (RFC 9728).
        
        Indicates that this resource server uses OAuth for authentication.
        """
        server_url = settings.get_server_url()
        
        return {
            "resource": server_url,
            "authorization_servers": [server_url],
            "scopes_supported": ["odoo:read", "odoo:write"],
            "bearer_methods_supported": ["header"]
        }
    
    @app.post("/oauth/register")
    async def oauth_register(request: Request):
        """
        OAuth 2.0 Dynamic Client Registration (RFC 7591).
        
        Allows OAuth clients like ChatGPT to register dynamically without pre-configuration.
        """
        try:
            body = await request.json()
            
            # Extraer parámetros del registro
            client_name = body.get("client_name", "Unknown Client")
            redirect_uris = body.get("redirect_uris", [])
            grant_types = body.get("grant_types")
            response_types = body.get("response_types")
            token_endpoint_auth_method = body.get("token_endpoint_auth_method", "client_secret_basic")
            scope = body.get("scope")
            
            # Validar redirect_uris
            if not redirect_uris:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="redirect_uris is required"
                )
            
            # Registrar cliente
            client_data = oauth_manager.register_client(
                client_name=client_name,
                redirect_uris=redirect_uris,
                grant_types=grant_types,
                response_types=response_types,
                token_endpoint_auth_method=token_endpoint_auth_method,
                scope=scope
            )
            
            logger.info(
                "client_registered_via_api",
                client_id=client_data["client_id"],
                client_name=client_name
            )
            
            return client_data
            
        except ValueError as e:
            logger.error("client_registration_error", error=str(e))
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
