"""OAuth 2.0 implementation for ChatGPT and other OAuth clients."""

import secrets
import hashlib
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()

# In-memory storage for OAuth (en producción usar Redis o DB)
oauth_codes: Dict[str, dict] = {}
oauth_tokens: Dict[str, dict] = {}


class OAuthManager:
    """Manage OAuth 2.0 flow for ChatGPT integration."""
    
    def __init__(self, client_id: str = "chatgpt-odoo-mcp", client_secret: Optional[str] = None):
        self.client_id = client_id
        self.client_secret = client_secret or secrets.token_urlsafe(32)
        self.code_expiry_seconds = 600  # 10 minutos
        self.token_expiry_seconds = 3600 * 24  # 24 horas
        
    def generate_authorization_code(
        self, 
        client_id: str, 
        redirect_uri: str, 
        state: Optional[str] = None,
        scope: Optional[str] = None
    ) -> str:
        """Generate authorization code for OAuth flow."""
        
        if client_id != self.client_id:
            logger.warning("invalid_client_id", client_id=client_id)
            raise ValueError("Invalid client_id")
        
        # Generar código de autorización único
        code = secrets.token_urlsafe(32)
        
        # Almacenar código con metadata
        oauth_codes[code] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": scope or "odoo:read odoo:write",
            "created_at": time.time(),
            "expires_at": time.time() + self.code_expiry_seconds
        }
        
        logger.info(
            "authorization_code_generated",
            code=code[:10] + "...",
            client_id=client_id,
            redirect_uri=redirect_uri
        )
        
        return code
    
    def exchange_code_for_token(
        self,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        
        # Validar código existe
        if code not in oauth_codes:
            logger.warning("invalid_authorization_code", code=code[:10] + "...")
            raise ValueError("Invalid authorization code")
        
        code_data = oauth_codes[code]
        
        # Validar código no expirado
        if time.time() > code_data["expires_at"]:
            del oauth_codes[code]
            logger.warning("expired_authorization_code", code=code[:10] + "...")
            raise ValueError("Authorization code expired")
        
        # Validar client_id
        if code_data["client_id"] != client_id:
            logger.warning("client_id_mismatch", expected=code_data["client_id"], got=client_id)
            raise ValueError("Client ID mismatch")
        
        # Validar client_secret
        if client_secret != self.client_secret:
            logger.warning("invalid_client_secret")
            raise ValueError("Invalid client secret")
        
        # Validar redirect_uri
        if code_data["redirect_uri"] != redirect_uri:
            logger.warning("redirect_uri_mismatch", expected=code_data["redirect_uri"], got=redirect_uri)
            raise ValueError("Redirect URI mismatch")
        
        # Generar access token
        access_token = secrets.token_urlsafe(48)
        refresh_token = secrets.token_urlsafe(48)
        
        # Almacenar token
        oauth_tokens[access_token] = {
            "client_id": client_id,
            "scope": code_data["scope"],
            "created_at": time.time(),
            "expires_at": time.time() + self.token_expiry_seconds,
            "refresh_token": refresh_token
        }
        
        # Eliminar código usado (one-time use)
        del oauth_codes[code]
        
        logger.info(
            "access_token_generated",
            token=access_token[:10] + "...",
            client_id=client_id,
            scope=code_data["scope"]
        )
        
        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": self.token_expiry_seconds,
            "refresh_token": refresh_token,
            "scope": code_data["scope"]
        }
    
    def validate_token(self, access_token: str) -> bool:
        """Validate OAuth access token."""
        
        if access_token not in oauth_tokens:
            logger.warning("invalid_access_token", token=access_token[:10] + "...")
            return False
        
        token_data = oauth_tokens[access_token]
        
        # Verificar expiración
        if time.time() > token_data["expires_at"]:
            del oauth_tokens[access_token]
            logger.warning("expired_access_token", token=access_token[:10] + "...")
            return False
        
        logger.debug("valid_access_token", token=access_token[:10] + "...")
        return True
    
    def refresh_access_token(
        self,
        refresh_token: str,
        client_id: str,
        client_secret: str
    ) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        
        # Buscar token por refresh_token
        old_token = None
        for token, data in oauth_tokens.items():
            if data.get("refresh_token") == refresh_token:
                old_token = token
                break
        
        if not old_token:
            logger.warning("invalid_refresh_token")
            raise ValueError("Invalid refresh token")
        
        token_data = oauth_tokens[old_token]
        
        # Validar client
        if token_data["client_id"] != client_id or client_secret != self.client_secret:
            logger.warning("invalid_client_credentials")
            raise ValueError("Invalid client credentials")
        
        # Generar nuevo access token
        new_access_token = secrets.token_urlsafe(48)
        new_refresh_token = secrets.token_urlsafe(48)
        
        # Almacenar nuevo token
        oauth_tokens[new_access_token] = {
            "client_id": client_id,
            "scope": token_data["scope"],
            "created_at": time.time(),
            "expires_at": time.time() + self.token_expiry_seconds,
            "refresh_token": new_refresh_token
        }
        
        # Eliminar token anterior
        del oauth_tokens[old_token]
        
        logger.info("access_token_refreshed", token=new_access_token[:10] + "...")
        
        return {
            "access_token": new_access_token,
            "token_type": "Bearer",
            "expires_in": self.token_expiry_seconds,
            "refresh_token": new_refresh_token,
            "scope": token_data["scope"]
        }
    
    def get_client_credentials(self) -> Dict[str, str]:
        """Get OAuth client credentials for setup."""
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
    
    def cleanup_expired(self):
        """Clean up expired codes and tokens."""
        current_time = time.time()
        
        # Limpiar códigos expirados
        expired_codes = [
            code for code, data in oauth_codes.items()
            if current_time > data["expires_at"]
        ]
        for code in expired_codes:
            del oauth_codes[code]
        
        # Limpiar tokens expirados
        expired_tokens = [
            token for token, data in oauth_tokens.items()
            if current_time > data["expires_at"]
        ]
        for token in expired_tokens:
            del oauth_tokens[token]
        
        if expired_codes or expired_tokens:
            logger.info(
                "oauth_cleanup",
                expired_codes=len(expired_codes),
                expired_tokens=len(expired_tokens)
            )


# Instancia global del OAuth manager
oauth_manager = OAuthManager()
