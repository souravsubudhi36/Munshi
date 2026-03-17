"""Claude tool/function definitions for all shop operations."""

from anthropic.types import ToolParam

MUNSHI_TOOLS: list[ToolParam] = [
    {
        "name": "add_sale",
        "description": "Record a sale transaction in the ledger. Use when the shop owner says they sold something.",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Sale amount in rupees"},
                "description": {"type": "string", "description": "What was sold (e.g. 'chai', 'atta 5kg')"},
                "category": {"type": "string", "description": "Product category (optional)"},
                "payment_mode": {
                    "type": "string",
                    "enum": ["cash", "upi", "card", "credit"],
                    "description": "How payment was made (default: cash)",
                },
            },
            "required": ["amount"],
        },
    },
    {
        "name": "add_expense",
        "description": "Record a business expense. Use when owner mentions spending money on supplies, rent, utilities, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Expense amount in rupees"},
                "description": {"type": "string", "description": "What the expense was for"},
                "category": {"type": "string", "description": "Expense category (optional)"},
            },
            "required": ["amount"],
        },
    },
    {
        "name": "add_udhar",
        "description": "Add a credit/udhar transaction — customer took goods without paying now.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string", "description": "Customer name or alias"},
                "amount": {"type": "number", "description": "Amount in rupees"},
                "description": {"type": "string", "description": "What items were taken (optional)"},
            },
            "required": ["customer_name", "amount"],
        },
    },
    {
        "name": "record_payment",
        "description": "Record that a credit customer has made a payment. Use when owner says customer paid back their udhar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string", "description": "Customer name or alias"},
                "amount": {"type": "number", "description": "Amount paid in rupees"},
            },
            "required": ["customer_name", "amount"],
        },
    },
    {
        "name": "get_outstanding",
        "description": "Get outstanding udhar balance for a customer or all customers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {
                    "type": "string",
                    "description": "Customer name (leave empty to get all customers with outstanding balance)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "check_stock",
        "description": "Check the current stock quantity of a product.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_name": {"type": "string", "description": "Product name in Hindi or English"},
            },
            "required": ["product_name"],
        },
    },
    {
        "name": "find_product_location",
        "description": "Find where a product is stored/located in the shop. Use when owner asks 'kahan hai' (where is).",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_name": {"type": "string", "description": "Product name in Hindi or English"},
            },
            "required": ["product_name"],
        },
    },
    {
        "name": "get_daily_summary",
        "description": "Get a summary of today's sales, expenses, and net profit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format (default: today)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "update_stock",
        "description": "Update stock quantity for a product (after receiving new inventory or adjustments).",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_name": {"type": "string"},
                "quantity": {
                    "type": "number",
                    "description": "Quantity to add (positive) or remove (negative)",
                },
                "movement_type": {
                    "type": "string",
                    "enum": ["purchase", "sale", "adjustment", "wastage"],
                    "description": "Type of stock movement",
                },
            },
            "required": ["product_name", "quantity"],
        },
    },
    {
        "name": "create_customer",
        "description": "Create a new customer profile for udhar tracking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Customer's name"},
                "phone": {"type": "string", "description": "Phone number (optional)"},
                "aliases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Alternative names/nicknames the customer is known by",
                },
            },
            "required": ["name"],
        },
    },
]
