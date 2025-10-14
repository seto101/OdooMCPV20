"""Authentication and authorization for HTTP mode."""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

from .config import Settings

logger = structlog.get_logger()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


class AuthManager:
    """Manages authentication and authorization."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.valid_api_keys = set(settings.get_api_keys())
    
    def verify_api_key(self, api_key: str) -> bool:
        """Verify if the API key is valid."""
        return api_key in self.valid_api_keys
    
    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.settings.access_token_expire_minutes
            )
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            self.settings.secret_key,
            algorithm=self.settings.algorithm
        )
        return encoded_jwt
    
    def verify_token(self, token: str) -> dict:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.settings.secret_key,
                algorithms=[self.settings.algorithm]
            )
            return payload
        except JWTError as e:
            logger.error("token_verification_failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def verify_request(
        self,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> dict:
        """Verify request authentication (API key or JWT token)."""
        token = credentials.credentials
        
        if self.verify_api_key(token):
            logger.info("api_key_authenticated")
            return {"auth_type": "api_key", "key": token}
        
        try:
            payload = self.verify_token(token)
            logger.info("jwt_authenticated", subject=payload.get("sub"))
            return {"auth_type": "jwt", "payload": payload}
        except HTTPException:
            logger.warning("authentication_failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)
