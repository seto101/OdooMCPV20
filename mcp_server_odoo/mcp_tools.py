"""FastMCP tools definition for streamable HTTP transport."""

from fastmcp import FastMCP
from typing import Annotated
from pydantic import Field
import structlog

from .config import get_settings
from .odoo_client import OdooClient
from .cache import CacheManager

logger = structlog.get_logger()

# Create FastMCP instance
mcp = FastMCP("odoo-mcp-server", version="2.0.0")


def get_odoo_client():
    """Get configured Odoo client."""
    settings = get_settings()
    cache_manager = CacheManager(ttl=settings.cache_ttl)
    return OdooClient(settings, cache_manager)


@mcp.tool()
async def odoo_search_records(
    model: Annotated[str, Field(description="The Odoo model name (e.g., 'res.partner', 'sale.order')")],
    domain: Annotated[list, Field(default=[], description="Search criteria as list of lists. Example: [['name', 'ilike', 'John']]", json_schema_extra={"type": "array", "items": {"type": "array", "items": {"type": "string"}}})] = [],
    limit: Annotated[int, Field(default=10, description="Maximum records to return")] = 10,
    offset: Annotated[int, Field(default=0, description="Number of records to skip")] = 0,
    order: Annotated[str | None, Field(default=None, description="Sort order (e.g., 'name asc')")] = None
) -> dict:
    """
    Search for records in any Odoo model using domain filters.
    
    This tool allows you to find records in Odoo models like customers (res.partner), 
    sales orders (sale.order), products (product.product), invoices (account.move), etc.
    
    Args:
        model: The Odoo model name (e.g., 'res.partner' for contacts, 'sale.order' for sales)
        domain: Search criteria as list of tuples. Examples:
                [['name', 'ilike', 'John']] - Find names containing 'John'
                [['email', '=', 'john@example.com']] - Exact email match
                [] - Empty domain returns all records (use with limit!)
        limit: Maximum records to return (default: 10, max recommended: 100)
        offset: Skip this many records (for pagination, default: 0)
        order: Sort order (e.g., 'name asc', 'create_date desc')
    
    Returns:
        Dictionary with success status, record IDs, and count
    """
    client = get_odoo_client()
    try:
        result = await client.search(model, domain, limit, offset, order)
        return {
            "success": True,
            "record_ids": result,
            "count": len(result),
            "message": f"Found {len(result)} record(s) in {model}"
        }
    except Exception as e:
        logger.error("search_error", model=model, error=str(e))
        return {
            "success": False,
            "error": str(e),
            "message": f"Error searching {model}"
        }


@mcp.tool()
async def odoo_read_records(
    model: Annotated[str, Field(description="The Odoo model name")],
    ids: Annotated[list[int], Field(description="List of record IDs to read")],
    fields: Annotated[list[str] | None, Field(default=None, description="Specific fields to retrieve")] = None
) -> dict:
    """
    Read detailed information from Odoo records.
    
    Use this after searching to get the actual data from records.
    
    Args:
        model: The Odoo model name
        ids: List of record IDs to read (from search results)
        fields: Specific fields to retrieve. If not specified, returns all fields.
                Common fields by model:
                - res.partner: name, email, phone, street, city, country_id
                - sale.order: name, partner_id, date_order, amount_total, state
                - product.product: name, default_code, list_price, qty_available
    
    Returns:
        Dictionary with success status, records data, and count
    """
    client = get_odoo_client()
    try:
        result = await client.read(model, ids, fields)
        return {
            "success": True,
            "records": result,
            "count": len(result),
            "message": f"Retrieved {len(result)} record(s) from {model}"
        }
    except Exception as e:
        logger.error("read_error", model=model, ids=ids, error=str(e))
        return {
            "success": False,
            "error": str(e),
            "message": f"Error reading from {model}"
        }


@mcp.tool()
async def odoo_search_read_records(
    model: Annotated[str, Field(description="The Odoo model name")],
    domain: Annotated[list, Field(default=[], description="Search criteria as list of lists", json_schema_extra={"type": "array", "items": {"type": "array", "items": {"type": "string"}}})] = [],
    fields: Annotated[list[str] | None, Field(default=None, description="Fields to retrieve")] = None,
    limit: Annotated[int, Field(default=10, description="Maximum records")] = 10,
    offset: Annotated[int, Field(default=0, description="Records to skip")] = 0,
    order: Annotated[str | None, Field(default=None, description="Sort order")] = None
) -> dict:
    """
    Combined search and read operation - finds and retrieves records in one call.
    
    This is more efficient than calling search + read separately.
    
    Args:
        model: The Odoo model name
        domain: Search criteria (same format as odoo_search_records)
        fields: Fields to retrieve in results
        limit: Maximum records (default: 10)
        offset: Records to skip (default: 0)
        order: Sort order
    
    Returns:
        Dictionary with success status, complete record data, and count
    """
    client = get_odoo_client()
    try:
        result = await client.search_read(model, domain, fields, limit, offset, order)
        return {
            "success": True,
            "records": result,
            "count": len(result),
            "message": f"Found and retrieved {len(result)} record(s) from {model}"
        }
    except Exception as e:
        logger.error("search_read_error", model=model, error=str(e))
        return {
            "success": False,
            "error": str(e),
            "message": f"Error searching and reading {model}"
        }


@mcp.tool()
async def odoo_create_record(
    model: Annotated[str, Field(description="The Odoo model name")],
    values: Annotated[dict, Field(description="Dictionary of field values for the new record")]
) -> dict:
    """
    Create a new record in Odoo.
    
    Use this to create customers, products, sales orders, invoices, or any other Odoo record.
    
    Args:
        model: The Odoo model name
        values: Dictionary of field values for the new record
                Examples:
                - res.partner: {'name': 'Company Name', 'email': 'email@example.com'}
                - product.product: {'name': 'Product Name', 'list_price': 100.0}
    
    Returns:
        Dictionary with success status and the new record ID
    """
    client = get_odoo_client()
    try:
        record_id = await client.create(model, values)
        return {
            "success": True,
            "record_id": record_id,
            "message": f"Successfully created record in {model} with ID {record_id}"
        }
    except Exception as e:
        logger.error("create_error", model=model, values=values, error=str(e))
        return {
            "success": False,
            "error": str(e),
            "message": f"Error creating record in {model}"
        }


@mcp.tool()
async def odoo_update_record(
    model: Annotated[str, Field(description="The Odoo model name")],
    ids: Annotated[list[int], Field(description="List of record IDs to update")],
    values: Annotated[dict, Field(description="Dictionary of field values to update")]
) -> dict:
    """
    Update existing records in Odoo.
    
    Modify one or more records by providing their IDs and the fields to update.
    
    Args:
        model: The Odoo model name
        ids: List of record IDs to update
        values: Dictionary of field values to update
    
    Returns:
        Dictionary with success status
    """
    client = get_odoo_client()
    try:
        result = await client.write(model, ids, values)
        return {
            "success": True,
            "updated": result,
            "count": len(ids),
            "message": f"Successfully updated {len(ids)} record(s) in {model}"
        }
    except Exception as e:
        logger.error("update_error", model=model, ids=ids, values=values, error=str(e))
        return {
            "success": False,
            "error": str(e),
            "message": f"Error updating records in {model}"
        }


@mcp.tool()
async def odoo_delete_record(
    model: Annotated[str, Field(description="The Odoo model name")],
    ids: Annotated[list[int], Field(description="List of record IDs to delete")]
) -> dict:
    """
    Delete records from Odoo (WARNING: This is permanent!).
    
    Use with caution - deleted records cannot be recovered.
    
    Args:
        model: The Odoo model name
        ids: List of record IDs to delete
    
    Returns:
        Dictionary with success status
    """
    client = get_odoo_client()
    try:
        result = await client.unlink(model, ids)
        return {
            "success": True,
            "deleted": result,
            "count": len(ids),
            "message": f"Successfully deleted {len(ids)} record(s) from {model}"
        }
    except Exception as e:
        logger.error("delete_error", model=model, ids=ids, error=str(e))
        return {
            "success": False,
            "error": str(e),
            "message": f"Error deleting records from {model}"
        }


@mcp.tool()
async def odoo_get_model_fields(
    model: Annotated[str, Field(description="The Odoo model name to inspect")]
) -> dict:
    """
    Get detailed information about fields in an Odoo model.
    
    Use this to discover what fields are available in a model, their types, and whether
    they're required. This is essential before creating or updating records.
    
    Args:
        model: The Odoo model name to inspect
    
    Returns:
        Dictionary with success status and field definitions
    """
    client = get_odoo_client()
    try:
        result = await client.get_fields(model)
        return {
            "success": True,
            "fields": result,
            "field_count": len(result),
            "message": f"Retrieved {len(result)} field definitions for {model}"
        }
    except Exception as e:
        logger.error("get_fields_error", model=model, error=str(e))
        return {
            "success": False,
            "error": str(e),
            "message": f"Error getting fields for {model}"
        }
