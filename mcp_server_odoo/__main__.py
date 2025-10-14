"""Main entry point for the MCP Odoo Server."""

import sys
import os
import structlog
from dotenv import load_dotenv

load_dotenv()

from .config import get_settings


def setup_logging():
    """Configure structured logging."""
    settings = get_settings()
    
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def main():
    """Main entry point."""
    setup_logging()
    
    logger = structlog.get_logger()
    
    settings = get_settings()
    
    if not settings.odoo_url or not settings.odoo_db or not settings.odoo_username or not settings.odoo_password:
        logger.warning(
            "missing_odoo_credentials",
            message="Odoo credentials not configured. Server will start but tools will not work until credentials are set."
        )
    
    logger.info(
        "mcp_odoo_server_starting",
        version="2.0.0",
        mode=settings.server_mode,
        odoo_url=settings.odoo_url or "Not configured"
    )
    
    if settings.server_mode == "http":
        logger.info("starting_http_mode", host=settings.host, port=settings.port)
        from .http_server import run_http_server
        run_http_server()
    else:
        logger.info("starting_stdio_mode")
        from .server import main as run_stdio
        run_stdio()


if __name__ == "__main__":
    main()
