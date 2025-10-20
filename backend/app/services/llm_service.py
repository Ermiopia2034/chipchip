from __future__ import annotations

import logging
from typing import Any, Dict, List

import google.generativeai as genai

from app.config import settings
from app.prompts.system_prompt import SYSTEM_PROMPT


def _schema(type_: str, properties: Dict[str, Any] | None = None, required: List[str] | None = None, items: Dict[str, Any] | None = None) -> Dict[str, Any]:
    s: Dict[str, Any] = {"type_": type_.upper()}
    if properties is not None:
        s["properties"] = properties
    if required:
        s["required"] = required
    if items is not None:
        s["items"] = items
    return s


def _tool_declarations() -> List[Dict[str, Any]]:
    # Gemini function declarations using Schema with type_ field and enum names
    fns = [
        {
            "name": "search_products",
            "description": "Search for products by name or category",
            "parameters": _schema(
                "OBJECT",
                properties={"query": _schema("STRING")},
                required=["query"],
            ),
        },
        {
            "name": "get_pricing_insights",
            "description": "Get competitor pricing and recommendations for a product",
            "parameters": _schema("OBJECT", properties={"product_name": _schema("STRING")}, required=["product_name"]),
        },
        {
            "name": "rag_query",
            "description": "Search product knowledge base for storage, nutrition, recipes, selection tips, seasonality",
            "parameters": _schema(
                "OBJECT",
                properties={
                    "query": _schema("STRING"),
                    "category": _schema("STRING"),
                },
                required=["query"],
            ),
        },
        {
            "name": "create_order",
            "description": "Create a customer order with delivery details",
            "parameters": _schema(
                "OBJECT",
                properties={
                    "items": _schema(
                        "ARRAY",
                        items=_schema(
                            "OBJECT",
                            properties={
                                "product_name": _schema("STRING"),
                                "quantity_kg": _schema("NUMBER"),
                            },
                            required=["product_name", "quantity_kg"],
                        ),
                    ),
                    "delivery_date": _schema("STRING"),
                    "delivery_location": _schema("STRING"),
                },
                required=["items", "delivery_date", "delivery_location"],
            ),
        },
        {
            "name": "add_inventory",
            "description": "Add product inventory for suppliers",
            "parameters": _schema(
                "OBJECT",
                properties={
                    "product_name": _schema("STRING"),
                    "quantity_kg": _schema("NUMBER"),
                    "price_per_unit": _schema("NUMBER"),
                    "available_date": _schema("STRING"),
                    "expiry_date": _schema("STRING"),
                    "generate_image": _schema("BOOLEAN"),
                },
                required=["product_name", "quantity_kg", "price_per_unit", "available_date"],
            ),
        },
        {
            "name": "check_supplier_stock",
            "description": "View supplier's current inventory",
            "parameters": _schema("OBJECT", properties={}),
        },
        {
            "name": "get_supplier_schedule",
            "description": "View supplier's delivery schedule",
            "parameters": _schema(
                "OBJECT",
                properties={
                    "start_date": _schema("STRING"),
                    "end_date": _schema("STRING"),
                },
            ),
        },
        {
            "name": "suggest_flash_sale",
            "description": "Check for expiring inventory and suggest discounts",
            "parameters": _schema("OBJECT", properties={}),
        },
        {
            "name": "get_customer_orders",
            "description": "View customer's orders with optional date range and status filter",
            "parameters": _schema(
                "OBJECT",
                properties={
                    "start_date": _schema("STRING"),
                    "end_date": _schema("STRING"),
                    "status": _schema("STRING"),
                },
            ),
        },
    ]
    return fns


def _wrap_tools(function_decls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Wrap function declarations into the SDK's Tool schema."""
    return [{"function_declarations": function_decls}]


class LLMService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._gen_config = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 2048,
        }
        # Default model with tools enabled for tool-calling phases
        self.model = genai.GenerativeModel(
            "gemini-2.5-pro",
            tools=_wrap_tools(_tool_declarations()),
            generation_config=self._gen_config,
        )

    def _build_system_prompt(self, user_type: str, registered: bool, user_name: str, context_summary: str, tool_descriptions: str) -> str:
        return SYSTEM_PROMPT.format(
            user_type=user_type,
            registered=registered,
            user_name=user_name,
            context_summary=context_summary,
            tool_descriptions=tool_descriptions,
        )

    def chat(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]] | None = None, allow_tools: bool = True) -> Dict[str, Any]:
        """
        Call Gemini with conversation messages and optional tool declarations.

        Returns dict with either:
        - {"type": "text", "content": str}
        - {"type": "tool_call", "name": str, "arguments": dict}
        """
        if allow_tools:
            model = self.model if tools is None else genai.GenerativeModel(
                "gemini-2.5-pro", tools=_wrap_tools(tools), generation_config=self._gen_config
            )
        else:
            # Finalization model without tools to avoid unintended tool calls or refusals
            model = genai.GenerativeModel("gemini-2.5-pro", generation_config=self._gen_config)

        # Convert our {role, content} messages into SDK-friendly contents
        def _coerce_messages(msgs: List[Dict[str, str]]):
            out = []
            for m in msgs:
                role = m.get("role", "user")
                content = m.get("content", "")
                out.append({"role": role, "parts": [content]})
            return out

        logger = logging.getLogger(__name__)
        try:
            logger.debug("LLM.chat start messages=%d tools=%s", len(messages), bool(tools))
        except Exception:
            pass
        resp = model.generate_content(_coerce_messages(messages))

        # Parse function/tool call if present
        try:
            # The SDK surfaces function calls in candidates' content parts
            cand = resp.candidates[0]
            for part in cand.content.parts:
                # FunctionCall types may be exposed as dict-like
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    out = {
                        "type": "tool_call",
                        "name": getattr(fc, "name", None) or fc.get("name"),
                        "arguments": getattr(fc, "args", None) or fc.get("args", {}),
                    }
                    try:
                        logger.info("LLM.tool_call name=%s", out.get("name"))
                    except Exception:
                        pass
                    return out
        except Exception:
            pass

        # Fallback to text (robust against multi-part responses)
        def _safe_text(r) -> str:
            try:
                # Avoid resp.text because it raises for multi-part responses
                pieces: List[str] = []
                for cand in getattr(r, "candidates", []) or []:
                    content = getattr(cand, "content", None)
                    parts = getattr(content, "parts", []) if content else []
                    for part in parts:
                        # part.text is typical for plain text parts
                        t = getattr(part, "text", None)
                        if t:
                            pieces.append(t)
                        else:
                            # Some SDK variants expose dict-like parts
                            if isinstance(part, dict):
                                v = part.get("text") or part.get("content")
                                if isinstance(v, str):
                                    pieces.append(v)
                return "\n".join(pieces).strip()
            except Exception:
                return ""

        text = _safe_text(resp)
        out = {"type": "text", "content": text or ""}
        try:
            logger.debug("LLM.text len=%d", len(out["content"]) if out["content"] else 0)
        except Exception:
            pass
        return out
