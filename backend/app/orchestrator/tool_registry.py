from __future__ import annotations

import logging
import datetime as dt
from typing import Any, Dict, List, Optional

from app.services.db_service import DatabaseService
from app.services.rag_service import VectorDBService
from app.services.image_service import ImageService
from app.orchestrator.session_manager import SessionManager
from app.config import settings


class ToolResult(dict):
    """Structured tool result: {success: bool, data: any, message: str}"""

    @staticmethod
    def ok(data: Any = None, message: str = "") -> "ToolResult":
        return ToolResult({"success": True, "data": data, "message": message})

    @staticmethod
    def fail(message: str, data: Any = None) -> "ToolResult":
        return ToolResult({"success": False, "data": data, "message": message})


class ToolRegistry:
    def __init__(self,
                 db: Optional[DatabaseService] = None,
                 rag: Optional[VectorDBService] = None,
                 images: Optional[ImageService] = None,
                 sessions: Optional[SessionManager] = None) -> None:
        self.db = db or DatabaseService()
        self.rag = rag or VectorDBService()
        self.images = images or ImageService()
        self.sessions = sessions or SessionManager()

        self._handlers = {
            "search_products": self.search_products_handler,
            "get_pricing_insights": self.get_pricing_insights_handler,
            "rag_query": self.rag_query_handler,
            "create_order": self.create_order_handler,
            "add_inventory": self.add_inventory_handler,
            "check_supplier_stock": self.check_supplier_stock_handler,
            "get_supplier_schedule": self.get_supplier_schedule_handler,
            "suggest_flash_sale": self.suggest_flash_sale_handler,
            "get_customer_orders": self.get_customer_orders_handler,
        }

    async def execute(self, name: str, args: Dict[str, Any], session_id: Optional[str] = None) -> ToolResult:
        handler = self._handlers.get(name)
        if not handler:
            return ToolResult.fail(f"Unknown tool: {name}")
        try:
            if settings.TRACE_TOOLS:
                logging.getLogger(__name__).info("TOOL CALL name=%s session=%s args=%s", name, session_id, _safe_args(args))
            res = await handler(args, session_id=session_id)
            if settings.TRACE_TOOLS:
                logging.getLogger(__name__).info("TOOL RESULT name=%s success=%s message=%s", name, bool(res.get("success")), _truncate(res.get("message", "")))
            return res
        except Exception as e:
            logging.getLogger(__name__).exception("Tool '%s' failed: %s", name, e)
            return ToolResult.fail(f"{name} failed: {e}")

    # ---------------- Handlers (class methods) ----------------
    async def search_products_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        query = str(args.get("query", "")).strip()
        if not query:
            return ToolResult.fail("query is required")

        products = await self.db.search_products(query)
        if not products:
            # Heuristic fallback: treat queries like "vegetables"/"fruits"/"dairy"
            target_cat = _normalize_category_query(query)
            if target_cat:
                all_prods = await self.db.get_all_products()
                products = [p for p in all_prods if _infer_category(p.product_name) == target_cat]
            if not products:
                return ToolResult.ok([], f"No products found matching '{query}'. Available categories: vegetables, fruits, dairy.")

        lines: List[str] = []
        data_out: List[Dict[str, Any]] = []
        for p in products:
            inv_list = await self.db.get_available_inventory(p.product_id)
            total_qty = sum(float(i.quantity_kg) for i in inv_list) if inv_list else 0.0
            price = min((float(i.price_per_unit) for i in inv_list), default=None)
            if price is not None and total_qty > 0:
                lines.append(f"{p.product_name}: {total_qty:.2f}kg available at {price:.2f} ETB/kg")
            else:
                lines.append(f"{p.product_name}: currently no active inventory")
            data_out.append({
                "product_id": p.product_id,
                "product_name": p.product_name,
                "available_quantity_kg": total_qty,
                "min_price_per_unit": price,
            })

        msg = f"Found {len(products)} products:\n" + "\n".join(lines)
        return ToolResult.ok(data_out, msg)

    async def get_pricing_insights_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        product_name = str(args.get("product_name", "")).strip()
        if not product_name:
            return ToolResult.fail("product_name is required")

        product = await self.db.get_product_by_name(product_name)
        if not product:
            return ToolResult.fail(f"Unknown product '{product_name}'")

        rec = await self.db.calculate_pricing_recommendation(product.product_id)

        def fmt(x: Any) -> str:
            try:
                return f"{float(x):.2f}"
            except Exception:
                return "N/A"

        msg = (
            f"Current market prices for {product.product_name}:\n"
            f"- Farm/Local: {fmt(rec.get('farm_avg'))} ETB/kg\n"
            f"- Supermarket: {fmt(rec.get('supermarket_avg'))} ETB/kg\n"
            f"- Distribution Center: {fmt(rec.get('distribution_avg'))} ETB/kg\n\n"
            f"Historical selling price: {fmt(rec.get('historical_avg'))} ETB/kg\n\n"
            f"Recommendation: Set price at {fmt(rec.get('recommended'))} ETB/kg for competitive positioning and quick turnover."
        )
        return ToolResult.ok(rec, msg)

    async def rag_query_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        query = str(args.get("query", "")).strip()
        category = args.get("category")
        if not query:
            return ToolResult.fail("query is required")

        result = self.rag.semantic_search(query, n_results=3, category=category)
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        scores = result.get("distances") or result.get("scores") or []
        # Chroma returns list-of-lists
        docs = documents[0] if documents and isinstance(documents[0], list) else documents
        metas = metadatas[0] if metadatas and isinstance(metadatas[0], list) else metadatas
        scs = scores[0] if scores and isinstance(scores[0], list) else scores

        if not docs:
            return ToolResult.ok([], "I don't have specific information about that. Let me help you with something else.")

        lines = []
        for i, d in enumerate(docs):
            meta = metas[i] if i < len(metas) else {}
            pn = meta.get("product_name")
            cat = meta.get("category")
            lines.append(f"- {pn} [{cat}]: {d}")
        msg = "Based on product knowledge:\n" + "\n".join(lines)
        packed = [
            {"content": docs[i], "metadata": metas[i] if i < len(metas) else {}, "score": scs[i] if i < len(scs) else None}
            for i in range(len(docs))
        ]
        return ToolResult.ok(packed, msg)

    async def create_order_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        if not session_id:
            return ToolResult.fail("session_id is required")
        session = await self.sessions.get_session(session_id)
        if not session or not session.get("registered"):
            return ToolResult.fail("User must be registered to create an order")
        customer_id = session.get("user_id")
        if not customer_id:
            return ToolResult.fail("Session missing user_id")

        items = args.get("items") or []
        delivery_date_raw = args.get("delivery_date")
        delivery_location = str(args.get("delivery_location", "")).strip()
        if not items or not delivery_date_raw or not delivery_location:
            return ToolResult.fail("items, delivery_date, and delivery_location are required")

        # Parse date
        if isinstance(delivery_date_raw, str):
            delivery_date = dt.date.fromisoformat(delivery_date_raw)
        elif isinstance(delivery_date_raw, dt.date):
            delivery_date = delivery_date_raw
        else:
            raise ValueError("Invalid delivery_date format")

        order_items: List[Dict[str, Any]] = []
        total = 0.0
        for it in items:
            pname = str(it.get("product_name"))
            qty = float(it.get("quantity_kg"))
            product = await self.db.get_product_by_name(pname)
            if not product:
                return ToolResult.fail(f"Unknown product '{pname}'")
            inv_list = await self.db.get_available_inventory(product.product_id)
            price = min((float(i.price_per_unit) for i in inv_list), default=None)
            if price is None:
                return ToolResult.fail(f"No available inventory for '{pname}'")
            total += qty * price
            order_items.append({
                "product_id": product.product_id,
                "quantity_kg": qty,
                "price_per_unit": price,
            })

        order_id = await self.db.create_order(customer_id, delivery_date, delivery_location, total)
        await self.db.add_order_items(order_id, order_items)

        items_list = ", ".join([f"{it['quantity_kg']}kg {it['product_id']}" for it in order_items])
        msg = (
            "Order confirmed! 🎉\n"
            f"Order ID: {order_id}\n"
            f"Items: {items_list}\n"
            f"Total: {total:.2f} ETB\n"
            f"Delivery: {delivery_date.isoformat()} to {delivery_location}\n"
            "Payment: Cash on Delivery\n"
        )
        return ToolResult.ok({"order_id": order_id, "total": total, "items": order_items}, msg)

    async def add_inventory_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        if not session_id:
            return ToolResult.fail("session_id is required")
        session = await self.sessions.get_session(session_id)
        if not session or session.get("user_type") != "supplier" or not session.get("registered"):
            return ToolResult.fail("User must be a registered supplier")
        supplier_id = session.get("user_id")

        pname = str(args.get("product_name", "")).strip()
        qty = float(args.get("quantity_kg"))
        ppu = float(args.get("price_per_unit"))
        avail_raw = args.get("available_date")
        expiry_raw = args.get("expiry_date")
        gen_img = bool(args.get("generate_image", False))

        if isinstance(avail_raw, str):
            available_date = dt.date.fromisoformat(avail_raw)
        else:
            available_date = avail_raw
        expiry_date = None
        if expiry_raw:
            expiry_date = dt.date.fromisoformat(expiry_raw) if isinstance(expiry_raw, str) else expiry_raw

        product = await self.db.get_product_by_name(pname)
        if not product:
            return ToolResult.fail(f"Unknown product '{pname}'")

        image_url = None
        if gen_img:
            try:
                image_url = self.images.generate_product_image(pname)
            except Exception as e:
                logging.getLogger(__name__).warning("Image generation failed for %s: %s", pname, e)

        inv_id = await self.db.add_inventory(
            supplier_id=supplier_id,
            product_id=product.product_id,
            quantity=qty,
            price=ppu,
            available_date=available_date,
            expiry_date=expiry_date,
            image_url=image_url,
        )

        msg = f"Inventory added: {pname} {qty}kg @ {ppu} ETB/kg (id={inv_id})"
        if image_url:
            msg += f"\nImage: {image_url}"
        elif gen_img:
            msg += "\nImage generation failed."
        return ToolResult.ok({"inventory_id": inv_id, "image_url": image_url}, msg)

    async def check_supplier_stock_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        if not session_id:
            return ToolResult.fail("session_id is required")
        session = await self.sessions.get_session(session_id)
        if not session or session.get("user_type") != "supplier" or not session.get("registered"):
            return ToolResult.fail("User must be a registered supplier")

        items = await self.db.get_supplier_inventory(session.get("user_id"))
        if not items:
            return ToolResult.ok([], "You have no inventory items yet.")
        lines = [
            f"{i+1}. {it['product_name']}: {it['quantity_kg']}kg @ {it['price_per_unit']} ETB/kg "
            f"(Available: {it['available_date']}{' Expires: ' + str(it['expiry_date']) if it['expiry_date'] else ''})"
            for i, it in enumerate(items)
        ]
        msg = "Your Current Inventory:\n" + "\n".join(lines)
        return ToolResult.ok(items, msg)

    async def get_supplier_schedule_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        if not session_id:
            return ToolResult.fail("session_id is required")
        session = await self.sessions.get_session(session_id)
        if not session or session.get("user_type") != "supplier" or not session.get("registered"):
            return ToolResult.fail("User must be a registered supplier")

        start_raw = args.get("start_date")
        end_raw = args.get("end_date")
        today = dt.date.today()
        # Default current week (Mon-Sun)
        if not start_raw or not end_raw:
            start_date = today - dt.timedelta(days=today.weekday())
            end_date = start_date + dt.timedelta(days=6)
        else:
            start_date = dt.date.fromisoformat(start_raw) if isinstance(start_raw, str) else start_raw
            end_date = dt.date.fromisoformat(end_raw) if isinstance(end_raw, str) else end_raw

        orders = await self.db.get_supplier_schedule(session.get("user_id"), start_date, end_date)
        if not orders:
            return ToolResult.ok([], "No confirmed orders scheduled in the selected range.")

        by_date: Dict[str, List[Dict[str, Any]]] = {}
        for o in orders:
            k = o["delivery_date"].isoformat()
            by_date.setdefault(k, []).append(o)

        lines: List[str] = ["Your Delivery Schedule:"]
        for k in sorted(by_date.keys()):
            count = len(by_date[k])
            total = sum(it.get("total_amount", 0.0) for it in by_date[k])
            when = dt.datetime.fromisoformat(k).strftime("%A, %b %d")
            lines.append(f"{when}: {count} orders ({total:.0f} ETB total)")

        return ToolResult.ok(orders, "\n".join(lines))

    async def suggest_flash_sale_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        if not session_id:
            return ToolResult.fail("session_id is required")
        session = await self.sessions.get_session(session_id)
        if not session or session.get("user_type") != "supplier" or not session.get("registered"):
            return ToolResult.fail("User must be a registered supplier")

        days_threshold = 3
        try:
            if isinstance(args.get("days_threshold"), int):
                days_threshold = int(args.get("days_threshold"))
        except Exception:
            pass

        expiring = await self.db.check_expiring_inventory(session.get("user_id"), days_threshold=days_threshold)
        if not expiring:
            return ToolResult.ok([], f"No expiring products in the next {days_threshold} days.")

        def discount_for(days_left: int) -> int:
            if days_left < 1:
                return 30
            return 20

        today = dt.date.today()
        lines = ["⚠️ Expiring Inventory Alert:"]
        suggestions: List[Dict[str, Any]] = []
        for it in expiring:
            days_left = (it["expiry_date"] - today).days
            pct = discount_for(days_left)
            new_price = round(float(it["price_per_unit"]) * (1 - pct / 100.0), 2)
            lines.append(
                f"- {it['product_name']} ({it['quantity_kg']} kg): Expires in {days_left} days → Suggest {pct}% flash sale"
            )
            suggestions.append({"inventory_id": it["inventory_id"], "discount_percent": pct, "new_price": new_price})

        return ToolResult.ok(suggestions, "\n".join(lines))

    async def get_customer_orders_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        if not session_id:
            return ToolResult.fail("session_id is required")
        session = await self.sessions.get_session(session_id)
        if not session or not session.get("registered"):
            return ToolResult.fail("User must be registered")
        customer_id = session.get("user_id")
        if not customer_id:
            return ToolResult.fail("Session missing user_id")

        status = args.get("status")
        start_raw = args.get("start_date")
        end_raw = args.get("end_date")
        start_date = None
        end_date = None
        try:
            if isinstance(start_raw, str):
                import datetime as dt
                start_date = dt.date.fromisoformat(start_raw)
            if isinstance(end_raw, str):
                import datetime as dt
                end_date = dt.date.fromisoformat(end_raw)
        except Exception:
            start_date = end_date = None

        orders = await self.db.get_customer_orders(customer_id, status)
        # Optional date filter on delivery_date if both dates present
        if start_date and end_date:
            orders = [o for o in orders if o.get("delivery_date") and start_date <= o["delivery_date"] <= end_date]

        if not orders:
            return ToolResult.ok([], "You have no orders in the selected range.")

        lines: List[str] = ["Your Orders:"]
        for o in orders:
            when = o.get("delivery_date")
            loc = o.get("delivery_location")
            total = o.get("total_amount")
            st = o.get("status")
            items = o.get("items") or []
            items_txt = ", ".join([f"{it['quantity_kg']}kg {it['product_name']}" for it in items if it.get('product_name')])
            lines.append(f"- {when}: {st} — {total:.2f} ETB — {items_txt} to {loc}")
        return ToolResult.ok(orders, "\n".join(lines))


def _truncate(s: str, n: int = 300) -> str:
    return (s or "")[:n] + ("…" if s and len(s) > n else "")


def _safe_args(args: Dict[str, Any], n: int = 500) -> str:
    try:
        import json

        text = json.dumps(args, ensure_ascii=False)
        return _truncate(text, n)
    except Exception:
        return str(args)

def _normalize_category_query(q: str) -> Optional[str]:
    t = (q or "").strip().lower()
    if t in {"veg", "veggies", "vegetable", "vegetables"}:
        return "vegetables"
    if t in {"fruit", "fruits"}:
        return "fruits"
    if t in {"dairy", "milk", "dairies"}:
        return "dairy"
    return None

def _infer_category(product_name: str) -> Optional[str]:
    n = (product_name or "").strip().lower()
    dairy_kw = ["milk", "yogurt", "butter", "cheese"]
    fruit_kw = [
        "apple", "banana", "avocado", "mango", "papaya", "orange", "lemon", "lime", "pineapple",
        "strawberry", "grape", "pear", "peach", "watermelon", "melon"
    ]
    veg_kw = [
        "tomato", "onion", "potato", "carrot", "cabbage", "spinach", "lettuce", "garlic", "ginger",
        "pepper", "capsicum", "cucumber", "eggplant", "zucchini", "beet", "kale"
    ]
    if any(k in n for k in dairy_kw):
        return "dairy"
    if any(k in n for k in fruit_kw):
        return "fruits"
    if any(k in n for k in veg_kw):
        return "vegetables"
    return None

    # ---------------- Handlers ----------------
    async def search_products_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        query = str(args.get("query", "")).strip()
        if not query:
            return ToolResult.fail("query is required")

        products = await self.db.search_products(query)
        if not products:
            return ToolResult.ok([], f"No products found matching '{query}'. Available categories: vegetables, fruits, dairy.")

        lines: List[str] = []
        data_out: List[Dict[str, Any]] = []
        for p in products:
            inv_list = await self.db.get_available_inventory(p.product_id)
            total_qty = sum(float(i.quantity_kg) for i in inv_list) if inv_list else 0.0
            price = min((float(i.price_per_unit) for i in inv_list), default=None)
            if price is not None and total_qty > 0:
                lines.append(f"{p.product_name}: {total_qty:.2f}kg available at {price:.2f} ETB/kg")
            else:
                lines.append(f"{p.product_name}: currently no active inventory")
            data_out.append({
                "product_id": p.product_id,
                "product_name": p.product_name,
                "available_quantity_kg": total_qty,
                "min_price_per_unit": price,
            })

        msg = f"Found {len(products)} products:\n" + "\n".join(lines)
        return ToolResult.ok(data_out, msg)

    async def get_pricing_insights_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        product_name = str(args.get("product_name", "")).strip()
        if not product_name:
            return ToolResult.fail("product_name is required")

        product = await self.db.get_product_by_name(product_name)
        if not product:
            return ToolResult.fail(f"Unknown product '{product_name}'")

        rec = await self.db.calculate_pricing_recommendation(product.product_id)
        msg = (
            f"Current market prices for {product.product_name}:\n"
            f"- Farm/Local: {rec.get('farm_avg')} ETB/kg\n"
            f"- Supermarket: {rec.get('supermarket_avg')} ETB/kg\n"
            f"- Distribution Center: {rec.get('distribution_avg')} ETB/kg\n\n"
            f"Historical selling price: {rec.get('historical_avg')} ETB/kg\n\n"
            f"Recommendation: Set price at {rec.get('recommended')} ETB/kg for competitive positioning and quick turnover."
        )
        return ToolResult.ok(rec, msg)

    async def rag_query_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        query = str(args.get("query", "")).strip()
        category = args.get("category")
        if not query:
            return ToolResult.fail("query is required")

        result = self.rag.semantic_search(query, n_results=3, category=category)
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        scores = result.get("distances") or result.get("scores") or []
        # Chroma returns list-of-lists
        docs = documents[0] if documents and isinstance(documents[0], list) else documents
        metas = metadatas[0] if metadatas and isinstance(metadatas[0], list) else metadatas
        scs = scores[0] if scores and isinstance(scores[0], list) else scores

        if not docs:
            return ToolResult.ok([], "I don't have specific information about that. Let me help you with something else.")

        lines = []
        for i, d in enumerate(docs):
            meta = metas[i] if i < len(metas) else {}
            pn = meta.get("product_name")
            cat = meta.get("category")
            lines.append(f"- {pn} [{cat}]: {d}")
        msg = "Based on product knowledge:\n" + "\n".join(lines)
        packed = [
            {"content": docs[i], "metadata": metas[i] if i < len(metas) else {}, "score": scs[i] if i < len(scs) else None}
            for i in range(len(docs))
        ]
        return ToolResult.ok(packed, msg)

    async def create_order_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        if not session_id:
            return ToolResult.fail("session_id is required")
        session = await self.sessions.get_session(session_id)
        if not session or not session.get("registered"):
            return ToolResult.fail("User must be registered to create an order")
        customer_id = session.get("user_id")
        if not customer_id:
            return ToolResult.fail("Session missing user_id")

        items = args.get("items") or []
        delivery_date_raw = args.get("delivery_date")
        delivery_location = str(args.get("delivery_location", "")).strip()
        if not items or not delivery_date_raw or not delivery_location:
            return ToolResult.fail("items, delivery_date, and delivery_location are required")

        # Parse date
        if isinstance(delivery_date_raw, str):
            delivery_date = dt.date.fromisoformat(delivery_date_raw)
        elif isinstance(delivery_date_raw, dt.date):
            delivery_date = delivery_date_raw
        else:
            raise ValueError("Invalid delivery_date format")

        order_items: List[Dict[str, Any]] = []
        total = 0.0
        for it in items:
            pname = str(it.get("product_name"))
            qty = float(it.get("quantity_kg"))
            product = await self.db.get_product_by_name(pname)
            if not product:
                return ToolResult.fail(f"Unknown product '{pname}'")
            inv_list = await self.db.get_available_inventory(product.product_id)
            price = min((float(i.price_per_unit) for i in inv_list), default=None)
            if price is None:
                return ToolResult.fail(f"No available inventory for '{pname}'")
            total += qty * price
            order_items.append({
                "product_id": product.product_id,
                "quantity_kg": qty,
                "price_per_unit": price,
            })

        order_id = await self.db.create_order(customer_id, delivery_date, delivery_location, total)
        await self.db.add_order_items(order_id, order_items)

        items_list = ", ".join([f"{it['quantity_kg']}kg {it['product_id']}" for it in order_items])
        msg = (
            "Order confirmed! 🎉\n"
            f"Order ID: {order_id}\n"
            f"Items: {items_list}\n"
            f"Total: {total:.2f} ETB\n"
            f"Delivery: {delivery_date.isoformat()} to {delivery_location}\n"
            "Payment: Cash on Delivery\n"
        )
        return ToolResult.ok({"order_id": order_id, "total": total, "items": order_items}, msg)

    async def add_inventory_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        if not session_id:
            return ToolResult.fail("session_id is required")
        session = await self.sessions.get_session(session_id)
        if not session or session.get("user_type") != "supplier" or not session.get("registered"):
            return ToolResult.fail("User must be a registered supplier")
        supplier_id = session.get("user_id")

        pname = str(args.get("product_name", "")).strip()
        qty = float(args.get("quantity_kg"))
        ppu = float(args.get("price_per_unit"))
        avail_raw = args.get("available_date")
        expiry_raw = args.get("expiry_date")
        gen_img = bool(args.get("generate_image", False))

        if isinstance(avail_raw, str):
            available_date = dt.date.fromisoformat(avail_raw)
        else:
            available_date = avail_raw
        expiry_date = None
        if expiry_raw:
            expiry_date = dt.date.fromisoformat(expiry_raw) if isinstance(expiry_raw, str) else expiry_raw

        product = await self.db.get_product_by_name(pname)
        if not product:
            return ToolResult.fail(f"Unknown product '{pname}'")

        image_url = None
        if gen_img:
            image_url = self.images.generate_product_image(pname)

        inv_id = await self.db.add_inventory(
            supplier_id=supplier_id,
            product_id=product.product_id,
            quantity=qty,
            price=ppu,
            available_date=available_date,
            expiry_date=expiry_date,
            image_url=image_url,
        )

        msg = f"Inventory added: {pname} {qty}kg @ {ppu} ETB/kg (id={inv_id})"
        if image_url:
            msg += f"\nImage: {image_url}"
        return ToolResult.ok({"inventory_id": inv_id, "image_url": image_url}, msg)

    async def check_supplier_stock_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        if not session_id:
            return ToolResult.fail("session_id is required")
        session = await self.sessions.get_session(session_id)
        if not session or session.get("user_type") != "supplier" or not session.get("registered"):
            return ToolResult.fail("User must be a registered supplier")

        items = await self.db.get_supplier_inventory(session.get("user_id"))
        if not items:
            return ToolResult.ok([], "You have no inventory items yet.")
        lines = [
            f"{i+1}. {it['product_name']}: {it['quantity_kg']}kg @ {it['price_per_unit']} ETB/kg "
            f"(Available: {it['available_date']}{' Expires: ' + str(it['expiry_date']) if it['expiry_date'] else ''})"
            for i, it in enumerate(items)
        ]
        msg = "Your Current Inventory:\n" + "\n".join(lines)
        return ToolResult.ok(items, msg)

    async def get_supplier_schedule_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        if not session_id:
            return ToolResult.fail("session_id is required")
        session = await self.sessions.get_session(session_id)
        if not session or session.get("user_type") != "supplier" or not session.get("registered"):
            return ToolResult.fail("User must be a registered supplier")

        start_raw = args.get("start_date")
        end_raw = args.get("end_date")
        today = dt.date.today()
        # Default current week (Mon-Sun)
        if not start_raw or not end_raw:
            start_date = today - dt.timedelta(days=today.weekday())
            end_date = start_date + dt.timedelta(days=6)
        else:
            start_date = dt.date.fromisoformat(start_raw) if isinstance(start_raw, str) else start_raw
            end_date = dt.date.fromisoformat(end_raw) if isinstance(end_raw, str) else end_raw

        orders = await self.db.get_supplier_schedule(session.get("user_id"), start_date, end_date)
        if not orders:
            return ToolResult.ok([], "No confirmed orders scheduled in the selected range.")

        by_date: Dict[str, List[Dict[str, Any]]] = {}
        for o in orders:
            k = o["delivery_date"].isoformat()
            by_date.setdefault(k, []).append(o)

        lines: List[str] = ["Your Delivery Schedule:"]
        for k in sorted(by_date.keys()):
            count = len(by_date[k])
            total = sum(it.get("total_amount", 0.0) for it in by_date[k])
            when = dt.datetime.fromisoformat(k).strftime("%A, %b %d")
            lines.append(f"{when}: {count} orders ({total:.0f} ETB total)")

        return ToolResult.ok(orders, "\n".join(lines))

    async def suggest_flash_sale_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        if not session_id:
            return ToolResult.fail("session_id is required")
        session = await self.sessions.get_session(session_id)
        if not session or session.get("user_type") != "supplier" or not session.get("registered"):
            return ToolResult.fail("User must be a registered supplier")

        expiring = await self.db.check_expiring_inventory(session.get("user_id"), days_threshold=3)
        if not expiring:
            return ToolResult.ok([], "No expiring products in the next 3 days.")

        def discount_for(days_left: int) -> int:
            if days_left < 1:
                return 30
            return 20

        today = dt.date.today()
        lines = ["⚠️ Expiring Inventory Alert:"]
        suggestions: List[Dict[str, Any]] = []
        for it in expiring:
            days_left = (it["expiry_date"] - today).days
            pct = discount_for(days_left)
            new_price = round(float(it["price_per_unit"]) * (1 - pct / 100.0), 2)
            lines.append(
                f"- {it['product_name']} ({it['quantity_kg']} kg): Expires in {days_left} days → Suggest {pct}% flash sale"
            )
            suggestions.append({"inventory_id": it["inventory_id"], "discount_percent": pct, "new_price": new_price})

        return ToolResult.ok(suggestions, "\n".join(lines))
