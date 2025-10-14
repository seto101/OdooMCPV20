"""MCP tools for Odoo with enhanced LLM-friendly descriptions."""

from typing import Any, Dict, List, Optional
from mcp.types import Tool, TextContent
import structlog
import json

from .odoo_client import OdooClient

logger = structlog.get_logger()


def get_tools() -> List[Tool]:
    """
    Get all available MCP tools with detailed, LLM-friendly descriptions.
    
    Each tool includes:
    - Clear, concise description
    - Detailed parameter explanations
    - Usage examples in descriptions
    - Common error scenarios
    """
    return [
        Tool(
            name="odoo_search_records",
            description="""Search for records in any Odoo model using domain filters.

This tool allows you to find records in Odoo models like customers (res.partner), 
sales orders (sale.order), products (product.product), invoices (account.move), etc.

Parameters:
- model: The Odoo model name (e.g., 'res.partner' for contacts, 'sale.order' for sales)
- domain: Search criteria as a list of tuples. Examples:
  * [['name', 'ilike', 'John']] - Find names containing 'John'
  * [['email', '=', 'john@example.com']] - Exact email match
  * [['create_date', '>=', '2024-01-01']] - Created after date
  * [] - Empty domain returns all records (use with limit!)
- limit: Maximum records to return (default: 10, max recommended: 100)
- offset: Skip this many records (for pagination, default: 0)
- order: Sort order (e.g., 'name asc', 'create_date desc')

Common operators for domain filters:
- '=' : equals
- '!=' : not equals
- '>' : greater than
- '<' : less than
- '>=' : greater or equal
- '<=' : less or equal
- 'like' : case-sensitive pattern
- 'ilike' : case-insensitive pattern
- 'in' : value in list
- 'not in' : value not in list

Returns: List of record IDs matching the criteria.

Example usage:
- Find customers named John: model='res.partner', domain=[['name', 'ilike', 'john']]
- Find unpaid invoices: model='account.move', domain=[['state', '=', 'posted'], ['payment_state', '=', 'not_paid']]
- Get recent sales orders: model='sale.order', order='create_date desc', limit=5""",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "Odoo model name (e.g., 'res.partner', 'sale.order', 'product.product')"
                    },
                    "domain": {
                        "type": "array",
                        "description": "Search domain as list of tuples [['field', 'operator', 'value']]",
                        "default": []
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of records to return",
                        "default": 10
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of records to skip (for pagination)",
                        "default": 0
                    },
                    "order": {
                        "type": "string",
                        "description": "Sort order (e.g., 'name asc', 'create_date desc')",
                        "default": None
                    }
                },
                "required": ["model"]
            }
        ),
        Tool(
            name="odoo_read_records",
            description="""Read detailed information from Odoo records.

Use this after searching to get the actual data from records. You need the record IDs
from a previous search operation.

Parameters:
- model: The Odoo model name
- ids: List of record IDs to read (from search results)
- fields: Specific fields to retrieve. If not specified, returns all fields.
  Common fields by model:
  * res.partner: name, email, phone, street, city, country_id
  * sale.order: name, partner_id, date_order, amount_total, state
  * product.product: name, default_code, list_price, qty_available
  * account.move: name, partner_id, invoice_date, amount_total, payment_state

Returns: List of dictionaries with record data.

Example usage:
- Read customer details: model='res.partner', ids=[1,2,3], fields=['name','email','phone']
- Get full sale order: model='sale.order', ids=[42]
- Read product info: model='product.product', ids=[10], fields=['name','list_price','qty_available']

Tip: Always specify fields to reduce data transfer and improve performance.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "Odoo model name"
                    },
                    "ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of record IDs to read"
                    },
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of field names to retrieve (omit for all fields)",
                        "default": None
                    }
                },
                "required": ["model", "ids"]
            }
        ),
        Tool(
            name="odoo_search_read_records",
            description="""Combined search and read operation - finds and retrieves records in one call.

This is more efficient than calling search + read separately. Use this when you want
to find records AND get their data immediately.

Parameters:
- model: The Odoo model name
- domain: Search criteria (same format as odoo_search_records)
- fields: Fields to retrieve in results
- limit: Maximum records (default: 10)
- offset: Records to skip (default: 0)
- order: Sort order

Returns: List of dictionaries with complete record data (not just IDs).

Example usage:
- Find and read customers: 
  model='res.partner', 
  domain=[['customer_rank', '>', 0]], 
  fields=['name', 'email', 'phone'],
  limit=20

- Get recent invoices with details:
  model='account.move',
  domain=[['create_date', '>=', '2024-01-01']],
  fields=['name', 'partner_id', 'amount_total', 'payment_state'],
  order='create_date desc'

Best practice: Use this instead of separate search + read for better performance.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "Odoo model name"
                    },
                    "domain": {
                        "type": "array",
                        "description": "Search domain",
                        "default": []
                    },
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Fields to retrieve",
                        "default": None
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum records",
                        "default": 10
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Records to skip",
                        "default": 0
                    },
                    "order": {
                        "type": "string",
                        "description": "Sort order",
                        "default": None
                    }
                },
                "required": ["model"]
            }
        ),
        Tool(
            name="odoo_create_record",
            description="""Create a new record in Odoo.

Use this to create customers, products, sales orders, invoices, or any other Odoo record.

Parameters:
- model: The Odoo model name
- values: Dictionary of field values for the new record

Required fields vary by model. Common examples:
- res.partner (customer): {'name': 'Company Name', 'email': 'email@example.com'}
- product.product: {'name': 'Product Name', 'list_price': 100.0}
- sale.order: {'partner_id': 123} (partner_id is required)

Many-to-one fields (like partner_id) need the ID of the related record.
Many-to-many fields use special syntax: [(6, 0, [id1, id2, id3])]

Returns: ID of the newly created record.

Example usage:
- Create customer: 
  model='res.partner',
  values={'name': 'John Doe', 'email': 'john@example.com', 'phone': '+1234567890'}

- Create product:
  model='product.product',
  values={'name': 'New Product', 'list_price': 99.99, 'type': 'consu'}

Important: Use odoo_get_model_fields first to see available fields and their requirements.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "Odoo model name"
                    },
                    "values": {
                        "type": "object",
                        "description": "Dictionary of field values for the new record"
                    }
                },
                "required": ["model", "values"]
            }
        ),
        Tool(
            name="odoo_update_record",
            description="""Update existing records in Odoo.

Modify one or more records by providing their IDs and the fields to update.

Parameters:
- model: The Odoo model name
- ids: List of record IDs to update
- values: Dictionary of field values to update

You can update multiple records at once if they should have the same values.
Only include fields you want to change - other fields remain unchanged.

Returns: True if successful.

Example usage:
- Update customer email:
  model='res.partner',
  ids=[42],
  values={'email': 'newemail@example.com'}

- Mark sale orders as urgent:
  model='sale.order',
  ids=[10, 11, 12],
  values={'priority': '1'}

- Update product price:
  model='product.product',
  ids=[5],
  values={'list_price': 129.99}

Tip: Read the record first to see current values before updating.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "Odoo model name"
                    },
                    "ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of record IDs to update"
                    },
                    "values": {
                        "type": "object",
                        "description": "Dictionary of field values to update"
                    }
                },
                "required": ["model", "ids", "values"]
            }
        ),
        Tool(
            name="odoo_delete_record",
            description="""Delete records from Odoo (WARNING: This is permanent!).

Use with caution - deleted records cannot be recovered.

Parameters:
- model: The Odoo model name
- ids: List of record IDs to delete

Returns: True if successful.

Important warnings:
- Deletion is permanent and cannot be undone
- Some records cannot be deleted due to constraints (e.g., invoices in 'posted' state)
- Deleting a record may affect related records
- Consider archiving instead (set 'active': False) for many models

Example usage:
- Delete draft sale order:
  model='sale.order',
  ids=[42]

- Delete multiple products:
  model='product.product',
  ids=[10, 11, 12]

Best practice: Always confirm with the user before deleting records.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "Odoo model name"
                    },
                    "ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of record IDs to delete"
                    }
                },
                "required": ["model", "ids"]
            }
        ),
        Tool(
            name="odoo_get_model_fields",
            description="""Get detailed information about fields in an Odoo model.

Use this to discover what fields are available in a model, their types, and whether
they're required. This is essential before creating or updating records.

Parameters:
- model: The Odoo model name

Returns: Dictionary of field definitions with:
- string: Human-readable field name
- type: Field type (char, integer, float, boolean, many2one, one2many, many2many, etc.)
- help: Description of the field's purpose
- required: Whether the field is mandatory
- readonly: Whether the field can be modified

Field types explained:
- char: Text string
- text: Long text
- integer: Whole number
- float: Decimal number
- boolean: True/False
- date: Date (YYYY-MM-DD)
- datetime: Date and time
- selection: Choose from predefined options
- many2one: Reference to another record (needs ID)
- one2many: List of related records
- many2many: Multiple references to other records

Example usage:
- Get partner fields: model='res.partner'
- Get product fields: model='product.product'
- Get invoice fields: model='account.move'

Best practice: Always check fields before creating/updating to avoid errors.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "Odoo model name to inspect"
                    }
                },
                "required": ["model"]
            }
        ),
    ]


async def handle_tool_call(
    tool_name: str,
    arguments: Dict[str, Any],
    odoo_client: OdooClient
) -> List[TextContent]:
    """
    Handle MCP tool calls with improved error handling and response formatting.
    
    Args:
        tool_name: Name of the tool being called
        arguments: Tool arguments
        odoo_client: Odoo client instance
        
    Returns:
        List of TextContent responses
    """
    logger.info("tool_call_started", tool=tool_name, arguments=arguments)
    
    try:
        if tool_name == "odoo_search_records":
            result = await odoo_client.search(
                model=arguments["model"],
                domain=arguments.get("domain", []),
                limit=arguments.get("limit", 10),
                offset=arguments.get("offset", 0),
                order=arguments.get("order")
            )
            response = {
                "success": True,
                "record_ids": result,
                "count": len(result),
                "message": f"Found {len(result)} record(s) in {arguments['model']}"
            }
            
        elif tool_name == "odoo_read_records":
            result = await odoo_client.read(
                model=arguments["model"],
                ids=arguments["ids"],
                fields=arguments.get("fields")
            )
            response = {
                "success": True,
                "records": result,
                "count": len(result),
                "message": f"Retrieved {len(result)} record(s) from {arguments['model']}"
            }
            
        elif tool_name == "odoo_search_read_records":
            result = await odoo_client.search_read(
                model=arguments["model"],
                domain=arguments.get("domain", []),
                fields=arguments.get("fields"),
                limit=arguments.get("limit", 10),
                offset=arguments.get("offset", 0),
                order=arguments.get("order")
            )
            response = {
                "success": True,
                "records": result,
                "count": len(result),
                "message": f"Found and retrieved {len(result)} record(s) from {arguments['model']}"
            }
            
        elif tool_name == "odoo_create_record":
            record_id = await odoo_client.create(
                model=arguments["model"],
                values=arguments["values"]
            )
            response = {
                "success": True,
                "record_id": record_id,
                "message": f"Successfully created record in {arguments['model']} with ID {record_id}"
            }
            
        elif tool_name == "odoo_update_record":
            result = await odoo_client.write(
                model=arguments["model"],
                ids=arguments["ids"],
                values=arguments["values"]
            )
            response = {
                "success": True,
                "updated": result,
                "count": len(arguments["ids"]),
                "message": f"Successfully updated {len(arguments['ids'])} record(s) in {arguments['model']}"
            }
            
        elif tool_name == "odoo_delete_record":
            result = await odoo_client.unlink(
                model=arguments["model"],
                ids=arguments["ids"]
            )
            response = {
                "success": True,
                "deleted": result,
                "count": len(arguments["ids"]),
                "message": f"Successfully deleted {len(arguments['ids'])} record(s) from {arguments['model']}"
            }
            
        elif tool_name == "odoo_get_model_fields":
            result = await odoo_client.get_fields(
                model=arguments["model"]
            )
            response = {
                "success": True,
                "fields": result,
                "field_count": len(result),
                "message": f"Retrieved {len(result)} field definitions for {arguments['model']}"
            }
            
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        logger.info("tool_call_succeeded", tool=tool_name)
        
        return [TextContent(
            type="text",
            text=json.dumps(response, indent=2, default=str)
        )]
        
    except Exception as e:
        logger.error("tool_call_failed", tool=tool_name, error=str(e))
        
        error_response = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "message": f"Error executing {tool_name}: {str(e)}",
            "suggestions": [
                "Check that the model name is correct",
                "Verify that field names match the model schema",
                "Ensure you have proper permissions",
                "Use odoo_get_model_fields to see available fields"
            ]
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(error_response, indent=2)
        )]
