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
            "parse_date_string": self.parse_date_string_handler,
            "get_current_time": self.get_current_time_handler,
            "register_user": self.register_user_handler,
            "search_products": self.search_products_handler,
            "get_pricing_insights": self.get_pricing_insights_handler,
            "rag_query": self.rag_query_handler,
            "create_order": self.create_order_handler,
            "add_inventory": self.add_inventory_handler,
            "generate_product_image": self.generate_product_image_handler,
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

    async def parse_date_string_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        """
        Parse a human date string relative to today and return an ISO date.

        Rules:
        - Accept month names ("Oct 25", "25 October") with optional year.
        - Accept numeric day-first formats common in Ethiopia ("25/10", "25-10").
        - If year is omitted, choose the next occurrence on or after today; if computed date is in the past, roll to next year.
        - Returns {"date": "YYYY-MM-DD"} in data and a short message.
        """
        import re
        today = dt.date.today()
        raw = str(args.get("text", "")).strip()
        if not raw:
            return ToolResult.fail("text is required")

        s = raw.lower().strip()
        # Quick keywords
        if s in {"today", "ማንኛውም ዛሬ", "ከዛሬ", "ትዕግስት ዛሬ"}:  # include rough Amharic variants
            return ToolResult.ok({"date": today.isoformat()}, f"Parsed date: {today.isoformat()}")
        if s in {"tomorrow", "ነገ"}:
            d = today + dt.timedelta(days=1)
            return ToolResult.ok({"date": d.isoformat()}, f"Parsed date: {d.isoformat()}")

        # Month name map
        months = {
            "jan": 1, "january": 1,
            "feb": 2, "february": 2,
            "mar": 3, "march": 3,
            "apr": 4, "april": 4,
            "may": 5,
            "jun": 6, "june": 6,
            "jul": 7, "july": 7,
            "aug": 8, "august": 8,
            "sep": 9, "sept": 9, "september": 9,
            "oct": 10, "october": 10,
            "nov": 11, "november": 11,
            "dec": 12, "december": 12,
        }

        def _mk_date(year: int, month: int, day: int) -> Optional[dt.date]:
            try:
                return dt.date(year, month, day)
            except Exception:
                return None

        # Pattern 1: Month name then day, optional year e.g., "oct 25", "october 25, 2025"
        m = re.search(r"\b(?P<mon>[a-zA-Z]{3,9})\s+(?P<day>\d{1,2})(?:\D+(?P<year>\d{4}))?\b", s)
        if m and m.group("mon").lower() in months:
            mon = months[m.group("mon").lower()]
            day = int(m.group("day"))
            year = int(m.group("year")) if m.group("year") else today.year
            candidate = _mk_date(year, mon, day)
            if candidate is None:
                return ToolResult.fail("Invalid date components")
            if not m.group("year") and candidate < today:
                candidate = _mk_date(year + 1, mon, day)
                if candidate is None:
                    return ToolResult.fail("Invalid date components")
            return ToolResult.ok({"date": candidate.isoformat()}, f"Parsed date: {candidate.isoformat()}")

        # Pattern 2: Day then month name e.g., "25 oct", "25 october 2025"
        m2 = re.search(r"\b(?P<day>\d{1,2})\s+(?P<mon>[a-zA-Z]{3,9})(?:\D+(?P<year>\d{4}))?\b", s)
        if m2 and m2.group("mon").lower() in months:
            mon = months[m2.group("mon").lower()]
            day = int(m2.group("day"))
            year = int(m2.group("year")) if m2.group("year") else today.year
            candidate = _mk_date(year, mon, day)
            if candidate is None:
                return ToolResult.fail("Invalid date components")
            if not m2.group("year") and candidate < today:
                candidate = _mk_date(year + 1, mon, day)
                if candidate is None:
                    return ToolResult.fail("Invalid date components")
            return ToolResult.ok({"date": candidate.isoformat()}, f"Parsed date: {candidate.isoformat()}")

        # Pattern 3: Numeric day-first common in Ethiopia: 25/10[/2025] or 25-10-2025
        m3 = re.search(r"\b(?P<a>\d{1,2})[/-](?P<b>\d{1,2})(?:[/-](?P<year>\d{4}))?\b", s)
        if m3:
            a = int(m3.group("a"))
            b = int(m3.group("b"))
            year = int(m3.group("year")) if m3.group("year") else today.year
            # Heuristic: prefer day-first; if the first number <=12 and second >12, swap
            if a <= 12 and b > 12:
                # Means a is month, b is day; swap to day-first
                day, month = b, a
            else:
                day, month = a, b
            candidate = _mk_date(year, month, day)
            if candidate is None:
                return ToolResult.fail("Invalid date components")
            if not m3.group("year") and candidate < today:
                candidate = _mk_date(year + 1, month, day)
                if candidate is None:
                    return ToolResult.fail("Invalid date components")
            return ToolResult.ok({"date": candidate.isoformat()}, f"Parsed date: {candidate.isoformat()}")

        return ToolResult.fail("Could not parse date string")

    async def get_current_time_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        import datetime as dt
        now = dt.datetime.now()
        today = now.date()
        # Week starts Monday
        mon = today - dt.timedelta(days=today.weekday())
        sun = mon + dt.timedelta(days=6)
        nxt_mon = mon + dt.timedelta(days=7)
        nxt_sun = nxt_mon + dt.timedelta(days=6)
        data = {
            "now_iso": now.isoformat(),
            "today": today.isoformat(),
            "current_week": {"start_date": mon.isoformat(), "end_date": sun.isoformat()},
            "next_week": {"start_date": nxt_mon.isoformat(), "end_date": nxt_sun.isoformat()},
        }
        msg = (
            f"Today is {today.isoformat()}. Current week: {mon.isoformat()} to {sun.isoformat()}. "
            f"Next week: {nxt_mon.isoformat()} to {nxt_sun.isoformat()}."
        )
        return ToolResult.ok(data, msg)

    async def register_user_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        """Register the current session as a customer or supplier and persist details.

        Required: user_type ("customer" | "supplier"), phone.
        Optional: name, location.
        """
        if not session_id:
            return ToolResult.fail("session_id is required")
        user_type_raw = str(args.get("user_type", "")).strip().lower()
        if user_type_raw not in {"customer", "supplier"}:
            return ToolResult.fail("user_type must be 'customer' or 'supplier'")
        phone = str(args.get("phone", "")).strip()
        if not phone:
            return ToolResult.fail("phone is required")
        name = (args.get("name") or "")
        location = (args.get("location") or "")

        # If phone already exists, treat as login and update session
        try:
            existing = await self.db.get_user_by_phone(phone)
        except Exception:
            existing = None
        if existing is not None:
            # Optionally keep existing user_type; if caller supplied a different type, prefer existing
            updates = {
                "user_id": str(existing.user_id),
                "user_type": existing.user_type or user_type_raw,
                "registered": True,
                "phone": existing.phone or phone,
                "name": existing.name or (name or None),
                "default_location": existing.default_location or (location or None),
            }
            await self.sessions.update_session(session_id, updates)
            msg = "You're already registered. I've logged you in to this session."
            return ToolResult.ok({"user_id": str(existing.user_id)}, msg)

        # Create new user and update session
        user_id = await self.db.create_user(phone, name or None, user_type_raw, location or None)
        updates = {
            "user_id": user_id,
            "user_type": user_type_raw,
            "registered": True,
            "phone": phone,
            "name": name or None,
            "default_location": location or None,
        }
        await self.sessions.update_session(session_id, updates)

        msg = f"Registration complete. Welcome {name or ''}! You are registered as a {user_type_raw}."
        return ToolResult.ok({"user_id": user_id}, msg)

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
        corrected_from: str | None = None
        if not product:
            # Fuzzy correction for obvious misspellings
            maybe, score = await self.db.fuzzy_get_product_by_name(product_name, threshold=0.8)
            if maybe is None:
                return ToolResult.fail(f"Unknown product '{product_name}'")
            corrected_from = product_name
            product = maybe

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
        if corrected_from:
            msg = f"I’ll use {product.product_name} (from '{corrected_from}').\n\n" + msg
        return ToolResult.ok(rec, msg)

    async def rag_query_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        query = str(args.get("query", "")).strip()
        category = (args.get("category") or "").strip() or None
        product_name_arg = (args.get("product_name") or "").strip() or None
        if not query:
            return ToolResult.fail("query is required")

        # Heuristic category detection from query if not provided
        ql = query.lower()
        if not category:
            if ("stor" in ql) or any(t in ql for t in ["store", "storage", "storing", "keep", "refrigerate", "fridge", "ripe", "ripen"]):
                category = "storage"
            elif any(t in ql for t in ["nutrition", "nutritional", "vitamin", "calories", "protein"]):
                category = "nutrition"
            elif any(t in ql for t in ["recipe", "recipes", "cook", "cooking"]):
                category = "recipes"
            elif any(t in ql for t in ["select", "selection", "choose", "pick"]):
                category = "selection"
            elif any(t in ql for t in ["season", "seasonality", "in season"]):
                category = "seasonality"

        # Try to infer product name from query if not provided
        product_name: Optional[str] = product_name_arg
        if not product_name:
            try:
                all_products = await self.db.get_all_products()
                for p in all_products:
                    pn = (p.product_name or "").strip()
                    if not pn:
                        continue
                    if pn.lower() in ql:
                        product_name = pn
                        break
                # Fuzzy fallback if no direct substring match
                if not product_name:
                    maybe, score = await self.db.fuzzy_get_product_by_name(query, threshold=0.8)
                    if maybe is not None:
                        product_name = maybe.product_name
            except Exception:
                # If DB not reachable, continue without a product filter
                pass

        # Narrow results: if we have a specific category or product, reduce n_results
        n_results = 1 if category in {"storage", "nutrition", "selection", "seasonality"} and product_name else 3
        result = self.rag.semantic_search(query, n_results=n_results, category=category, product_name=product_name)
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        scores = result.get("distances") or result.get("scores") or []
        # Chroma returns list-of-lists
        docs = documents[0] if documents and isinstance(documents[0], list) else documents
        metas = metadatas[0] if metadatas and isinstance(metadatas[0], list) else metadatas
        scs = scores[0] if scores and isinstance(scores[0], list) else scores

        if not docs:
            return ToolResult.ok([], "I don't have specific information about that. Let me help you with something else.")

        # Prefer concise single answer when focused filters are present
        if product_name and category and docs:
            primary = docs[0]
            msg = primary
            # If the KB content is in the form "<Product> <category>: <content>", strip the prefix for brevity
            try:
                parts = primary.split(":", 1)
                if len(parts) == 2 and product_name.lower() in parts[0].lower():
                    msg = parts[1].strip()
            except Exception:
                pass
            return ToolResult.ok([
                {"content": docs[0], "metadata": metas[0] if metas else {}, "score": scs[0] if scs else None}
            ], msg)

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
        # Guard against past dates
        if delivery_date < dt.date.today():
            return ToolResult.fail(f"Delivery date {delivery_date.isoformat()} is in the past. Please choose today or a future date.")

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
                "product_name": product.product_name,
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
        return ToolResult.ok({
            "order_id": order_id,
            "total": total,
            "items": order_items,
            "delivery_date": delivery_date.isoformat(),
            "delivery_location": delivery_location,
            "payment": "Cash on Delivery",
        }, msg)

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
        corrected_from2: str | None = None
        if not product:
            maybe, score = await self.db.fuzzy_get_product_by_name(pname, threshold=0.8)
            if maybe is None:
                return ToolResult.fail(f"Unknown product '{pname}'")
            corrected_from2 = pname
            product = maybe

        image_url = None
        if gen_img:
            try:
                # Use canonical product name for image prompt
                image_url = self.images.generate_product_image(product.product_name)
            except Exception as e:
                logging.getLogger(__name__).warning("Image generation failed for %s: %s", product.product_name, e)

        inv_id = await self.db.add_inventory(
            supplier_id=supplier_id,
            product_id=product.product_id,
            quantity=qty,
            price=ppu,
            available_date=available_date,
            expiry_date=expiry_date,
            image_url=image_url,
        )

        canonical = product.product_name
        msg = f"Inventory added: {canonical} {qty}kg @ {ppu} ETB/kg (id={inv_id})"
        if image_url:
            msg += f"\nImage: {image_url}"
        elif gen_img:
            msg += "\nImage generation failed."
        if corrected_from2:
            msg = f"I’ll use {canonical} (from '{corrected_from2}').\n" + msg
        return ToolResult.ok({"inventory_id": inv_id, "image_url": image_url}, msg)

    async def generate_product_image_handler(self, args: Dict[str, Any], *, session_id: Optional[str]) -> ToolResult:
        """Generate an image for a product and return its URL."""
        pname_arg = str(args.get("product_name", "")).strip()
        query = str(args.get("query", "")).strip()
        pname = pname_arg or query
        if not pname:
            return ToolResult.fail("product_name is required")

        # Normalize to canonical product name
        ql = pname.lower()
        product = await self.db.get_product_by_name(pname)
        corrected_from: str | None = None
        if not product:
            try:
                # Try substring match against catalog first
                all_products = await self.db.get_all_products()
                for p in all_products:
                    pn = (p.product_name or "").strip()
                    if pn and pn.lower() in ql:
                        product = p
                        corrected_from = pname
                        break
            except Exception:
                pass
        if not product:
            maybe, score = await self.db.fuzzy_get_product_by_name(pname, threshold=0.65)
            if maybe is None:
                return ToolResult.fail(f"Unknown product '{pname}'")
            corrected_from = pname
            product = maybe

        try:
            url = self.images.generate_product_image(product.product_name)
        except Exception as e:
            return ToolResult.fail(f"Image generation failed: {e}")

        msg = f"Image generated for {product.product_name}: {url}"
        if corrected_from:
            msg = f"I’ll use {product.product_name} (from '{corrected_from}').\n" + msg
        return ToolResult.ok({"image_url": url, "product_name": product.product_name}, msg)

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
        # Guard against past dates
        if delivery_date < dt.date.today():
            return ToolResult.fail(f"Delivery date {delivery_date.isoformat()} is in the past. Please choose today or a future date.")

        order_items: List[Dict[str, Any]] = []
        total = 0.0
        for it in items:
            pname = str(it.get("product_name"))
            qty = float(it.get("quantity_kg"))
            product = await self.db.get_product_by_name(pname)
            if not product:
                maybe, score = await self.db.fuzzy_get_product_by_name(pname, threshold=0.8)
                if maybe is None:
                    return ToolResult.fail(f"Unknown product '{pname}'")
                product = maybe
            inv_list = await self.db.get_available_inventory(product.product_id)
            price = min((float(i.price_per_unit) for i in inv_list), default=None)
            if price is None:
                return ToolResult.fail(f"No available inventory for '{pname}'")
            total += qty * price
            order_items.append({
                "product_id": product.product_id,
                "product_name": product.product_name,
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
        return ToolResult.ok({
            "order_id": order_id,
            "total": total,
            "items": order_items,
            "delivery_date": delivery_date.isoformat(),
            "delivery_location": delivery_location,
            "payment": "Cash on Delivery",
        }, msg)

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
