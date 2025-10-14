"""Enhanced Odoo client with error handling and retries."""

import xmlrpc.client
import ssl
from typing import Any, Dict, List, Optional, Union
import structlog
from time import sleep

from .config import Settings
from .cache import CacheManager

logger = structlog.get_logger()


class OdooClientError(Exception):
    """Base exception for Odoo client errors."""
    pass


class OdooAuthenticationError(OdooClientError):
    """Authentication failed."""
    pass


class OdooConnectionError(OdooClientError):
    """Connection to Odoo failed."""
    pass


class OdooClient:
    """
    Enhanced Odoo XML-RPC client with:
    - Automatic retries with exponential backoff
    - Better error handling and logging
    - Optional caching for read operations
    - SSL support
    """
    
    def __init__(self, settings: Settings, cache_manager: Optional[CacheManager] = None):
        self.settings = settings
        self.cache_manager = cache_manager
        self.url = settings.odoo_url.rstrip('/')
        self.db = settings.odoo_db
        self.username = settings.odoo_username
        self.password = settings.odoo_password
        self.timeout = settings.odoo_timeout
        self.max_retries = settings.odoo_max_retries
        
        self._uid: Optional[int] = None
        self._common_proxy = None
        self._object_proxy = None
        
        logger.info("odoo_client_initialized", url=self.url, db=self.db)
    
    def _get_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context for secure connections."""
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        return context
    
    def _get_proxy(self, endpoint: str):
        """Get XML-RPC proxy for an endpoint."""
        url = f"{self.url}/xmlrpc/2/{endpoint}"
        
        if self.url.startswith('https'):
            context = self._get_ssl_context()
            return xmlrpc.client.ServerProxy(
                url,
                context=context,
                allow_none=True
            )
        else:
            return xmlrpc.client.ServerProxy(url, allow_none=True)
    
    @property
    def common(self):
        """Get common proxy."""
        if not self._common_proxy:
            self._common_proxy = self._get_proxy('common')
        return self._common_proxy
    
    @property
    def models(self):
        """Get object/models proxy."""
        if not self._object_proxy:
            self._object_proxy = self._get_proxy('object')
        return self._object_proxy
    
    def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with retry logic and exponential backoff."""
        last_error: Exception = Exception("No attempts made")
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        "retrying_odoo_call",
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        wait_time=wait_time,
                        error=str(e)
                    )
                    sleep(wait_time)
                else:
                    logger.error(
                        "odoo_call_failed",
                        attempts=self.max_retries,
                        error=str(e)
                    )
        
        raise last_error
    
    def authenticate(self) -> int:
        """
        Authenticate with Odoo and return user ID.
        
        Returns:
            int: User ID
            
        Raises:
            OdooAuthenticationError: If authentication fails
        """
        if self._uid:
            return self._uid
        
        try:
            logger.info("authenticating_with_odoo", username=self.username)
            
            uid = self._retry_with_backoff(
                self.common.authenticate,
                self.db,
                self.username,
                self.password,
                {}
            )
            
            if not uid:
                raise OdooAuthenticationError(
                    f"Authentication failed for user '{self.username}' on database '{self.db}'"
                )
            
            self._uid = int(uid)
            logger.info("authentication_successful", uid=int(uid))
            return int(uid)
            
        except Exception as e:
            logger.error("authentication_error", error=str(e))
            raise OdooAuthenticationError(f"Authentication error: {str(e)}")
    
    def execute_kw(
        self,
        model: str,
        method: str,
        args: Optional[List] = None,
        kwargs: Optional[Dict] = None
    ) -> Any:
        """
        Execute a method on an Odoo model.
        
        Args:
            model: Odoo model name (e.g., 'res.partner')
            method: Method to call (e.g., 'search', 'read')
            args: Positional arguments
            kwargs: Keyword arguments
            
        Returns:
            Result from Odoo
            
        Raises:
            OdooClientError: If the call fails
        """
        args = args if args is not None else []
        kwargs = kwargs if kwargs is not None else {}
        
        try:
            uid = self.authenticate()
            
            logger.debug(
                "executing_odoo_method",
                model=model,
                method=method,
                args=args,
                kwargs=kwargs
            )
            
            result = self._retry_with_backoff(
                self.models.execute_kw,
                self.db,
                uid,
                self.password,
                model,
                method,
                args,
                kwargs
            )
            
            logger.debug("odoo_method_success", model=model, method=method)
            return result
            
        except Exception as e:
            logger.error(
                "odoo_method_error",
                model=model,
                method=method,
                error=str(e)
            )
            raise OdooClientError(f"Error calling {model}.{method}: {str(e)}")
    
    async def search(
        self,
        model: str,
        domain: Optional[List] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order: Optional[str] = None
    ) -> List[int]:
        """
        Search for records in Odoo.
        
        Args:
            model: Odoo model name
            domain: Search domain
            limit: Maximum number of records
            offset: Number of records to skip
            order: Sort order
            
        Returns:
            List of record IDs
        """
        domain = domain if domain is not None else []
        kwargs: Dict[str, Any] = {'offset': offset}
        
        if limit is not None:
            kwargs['limit'] = limit
        if order:
            kwargs['order'] = order
        
        cache_key = None
        if self.cache_manager and limit and limit <= 100:
            cache_key = self.cache_manager._make_key(
                "search", model, str(domain), str(limit), str(offset), str(order)
            )
            cached = await self.cache_manager.get(cache_key)
            if cached is not None:
                return cached
        
        result = self.execute_kw(model, 'search', [domain], kwargs)
        
        if cache_key:
            await self.cache_manager.set(cache_key, result)
        
        return result
    
    async def read(
        self,
        model: str,
        ids: List[int],
        fields: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Read records from Odoo.
        
        Args:
            model: Odoo model name
            ids: List of record IDs
            fields: List of fields to read
            
        Returns:
            List of record dictionaries
        """
        kwargs = {}
        if fields:
            kwargs['fields'] = fields
        
        return self.execute_kw(model, 'read', [ids], kwargs)
    
    async def search_read(
        self,
        model: str,
        domain: Optional[List] = None,
        fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order: Optional[str] = None
    ) -> List[Dict]:
        """
        Search and read records in one call.
        
        Args:
            model: Odoo model name
            domain: Search domain
            fields: Fields to read
            limit: Maximum number of records
            offset: Number of records to skip
            order: Sort order
            
        Returns:
            List of record dictionaries
        """
        domain = domain if domain is not None else []
        kwargs: Dict[str, Any] = {'offset': offset}
        
        if fields:
            kwargs['fields'] = fields
        if limit is not None:
            kwargs['limit'] = limit
        if order:
            kwargs['order'] = order
        
        return self.execute_kw(model, 'search_read', [domain], kwargs)
    
    async def create(self, model: str, values: Dict) -> int:
        """
        Create a record in Odoo.
        
        Args:
            model: Odoo model name
            values: Field values for the new record
            
        Returns:
            ID of created record
        """
        return self.execute_kw(model, 'create', [values])
    
    async def write(self, model: str, ids: List[int], values: Dict) -> bool:
        """
        Update records in Odoo.
        
        Args:
            model: Odoo model name
            ids: List of record IDs to update
            values: Field values to update
            
        Returns:
            True if successful
        """
        return self.execute_kw(model, 'write', [ids, values])
    
    async def unlink(self, model: str, ids: List[int]) -> bool:
        """
        Delete records from Odoo.
        
        Args:
            model: Odoo model name
            ids: List of record IDs to delete
            
        Returns:
            True if successful
        """
        return self.execute_kw(model, 'unlink', [ids])
    
    async def get_fields(self, model: str) -> Dict[str, Any]:
        """
        Get field definitions for a model.
        
        Args:
            model: Odoo model name
            
        Returns:
            Dictionary of field definitions
        """
        cache_key = None
        if self.cache_manager:
            cache_key = self.cache_manager._make_key("fields", model)
            cached = await self.cache_manager.get(cache_key)
            if cached is not None:
                return cached
        
        result = self.execute_kw(model, 'fields_get', [], {'attributes': ['string', 'type', 'help']})
        
        if cache_key:
            await self.cache_manager.set(cache_key, result, ttl=3600)
        
        return result
