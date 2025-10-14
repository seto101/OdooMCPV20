"""MCP stdio server implementation for Claude Desktop and local AI assistants."""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
import structlog

from .config import get_settings
from .odoo_client import OdooClient
from .cache import CacheManager
from .tools import get_tools, handle_tool_call

logger = structlog.get_logger()


async def run_stdio_server():
    """Run the MCP server in stdio mode for local AI assistants."""
    
    logger.info("starting_stdio_server")
    
    settings = get_settings()
    
    cache_manager = CacheManager(ttl=settings.cache_ttl)
    
    odoo_client = OdooClient(settings, cache_manager)
    
    server = Server("odoo-mcp-server")
    
    @server.list_tools()
    async def list_tools():
        """List all available tools."""
        logger.debug("listing_tools")
        return get_tools()
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        """Handle tool calls."""
        logger.info("tool_called", tool=name)
        return await handle_tool_call(name, arguments, odoo_client)
    
    logger.info("stdio_server_ready", odoo_url=settings.odoo_url)
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """Entry point for stdio server."""
    try:
        asyncio.run(run_stdio_server())
    except KeyboardInterrupt:
        logger.info("server_stopped_by_user")
    except Exception as e:
        logger.error("server_error", error=str(e))
        raise
