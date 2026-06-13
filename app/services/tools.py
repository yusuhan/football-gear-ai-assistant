"""Tool router used by the Agent.

The methods in this file are intentionally ordinary Python functions. They map
directly to OpenAI function-calling tool definitions, but can also be executed
without an external LLM for deterministic local demos.
"""

from typing import Any, Optional

from app.services.product_repository import ProductRepository


class ToolRouter:
    """Execute product, inventory and size tools."""

    def __init__(self, repository: ProductRepository) -> None:
        self.repository = repository

    def check_inventory(self, product_name: str, size: int) -> dict[str, Any]:
        """Check stock for a product and shoe size."""

        result = self.repository.check_inventory(product_name=product_name, size=size)
        if not result:
            return {"available": False, "product_name": product_name, "size": size, "stock": 0}
        return {"available": result["stock"] > 0, **result}

    def search_products(
        self,
        position: Optional[str] = None,
        budget: Optional[int] = None,
        fit_profile: Optional[str] = None,
        category: Optional[str] = None,
    ) -> dict[str, Any]:
        """Search products by category, position, budget and boot fit."""

        products = self.repository.search_products(
            position=position,
            budget=budget,
            fit_profile=fit_profile,
            category=category,
        )
        return {"products": products, "count": len(products)}

    def get_size_recommendation(self, foot_length: float) -> dict[str, Any]:
        """Recommend football boot size by foot length in centimeters."""

        result = self.repository.get_size_recommendation(foot_length=foot_length)
        if not result:
            return {"foot_length": foot_length, "recommended_size": None}
        return {"foot_length": foot_length, "recommended_size": result["recommended_size"]}

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool by name."""

        if name == "check_inventory":
            return self.check_inventory(
                product_name=str(arguments["product_name"]),
                size=int(arguments["size"]),
            )
        if name == "search_products":
            budget = arguments.get("budget")
            return self.search_products(
                position=arguments.get("position"),
                budget=int(budget) if budget is not None else None,
                fit_profile=arguments.get("fit_profile"),
                category=arguments.get("category"),
            )
        if name == "get_size_recommendation":
            return self.get_size_recommendation(foot_length=float(arguments["foot_length"]))
        raise ValueError(f"Unknown tool: {name}")


OPENAI_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "check_inventory",
            "description": "Check inventory for a football gear product and size.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string"},
                    "size": {"type": "integer"},
                },
                "required": ["product_name", "size"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search football gear by category, player position, budget and boot fit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "position": {"type": "string"},
                    "budget": {"type": "integer"},
                    "fit_profile": {
                        "type": "string",
                        "enum": ["narrow", "regular", "wide"],
                    },
                    "category": {
                        "type": "string",
                        "enum": [
                            "football_boots",
                            "football_apparel",
                            "football_socks",
                            "shin_guards",
                            "footballs",
                            "goalkeeper_gloves",
                            "protective_gear"
                        ]
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_size_recommendation",
            "description": "Recommend boot size from foot length in centimeters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "foot_length": {"type": "number"},
                },
                "required": ["foot_length"],
            },
        },
    },
]
