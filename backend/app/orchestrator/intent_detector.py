from __future__ import annotations

import json
import datetime as dt
from typing import Any, Dict
import re

import google.generativeai as genai

from app.config import settings


INTENTS = [
    "registration_customer",
    "registration_supplier",
    "product_inquiry",
    "knowledge_query",
    "image_generation",
    "place_order",
    "check_customer_orders",
    "add_inventory",
    "check_stock",
    "check_schedule",
    "flash_sale_check",
    "general_chat",
]


class IntentDetector:
    """LLM-only intent detection using a fast Gemini Flash model."""

    def __init__(self, model: str = "models/gemini-flash-latest") -> None:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model_name = model
        self.model = genai.GenerativeModel(self.model_name)

    def detect(self, text: str) -> Dict[str, Any]:
        """Return {intent: str, entities: dict}. Adds light rule fallback for reliability."""
        # 1) Lightweight rule-based shortcut for common cases (no network needed)
        t = (text or "").strip()
        entities: Dict[str, Any] = {}

        # Extract Ethiopian phone numbers in common forms: 09XXXXXXXX, +2519XXXXXXXX, 2519XXXXXXXX
        phone = _extract_phone(t)
        if phone:
            entities["phone"] = phone

        # Heuristic intent if registration keywords present
        lt = t.lower()
        if any(k in lt for k in ["register", "sign up", "signup", "sign-up"]) or (
            phone and any(k in lt for k in ["customer", "supplier"])  # phone alongside a user type
        ):
            user_type = "supplier" if "supplier" in lt else "customer"
            # Extract simple name and location if present
            name = _extract_name(t)
            location = _extract_location(t)
            if name:
                entities["name"] = name
            if location:
                entities["location"] = location
            return {"intent": f"registration_{user_type}", "entities": entities}

        # Add inventory heuristics: detect structured supplier additions
        # Triggers: phrases like "add inventory", or patterns with kg + ETB and availability
        if (
            "add inventory" in lt
            or ("add" in lt and "kg" in lt and ("etb" in lt or "etb/kg" in lt))
            or ("available date" in lt and "expiry date" in lt)
        ):
            # Extract fields
            qty_m = re.search(r"(\d+(?:\.\d+)?)\s*kg", t, flags=re.IGNORECASE)
            price_m = re.search(r"at\s*([0-9]+(?:\.[0-9]+)?)\s*etb(?:/kg)?", t, flags=re.IGNORECASE)
            # Product name commonly appears as "kg of <name>" before price
            pname_m = re.search(r"kg\s+of\s+([A-Za-z\u1200-\u137F'\- ]+?)\s*(?:at|,|\.|$)", t, flags=re.IGNORECASE)
            avail_m = re.search(r"available\s*date\s*:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", t, flags=re.IGNORECASE)
            exp_m = re.search(r"expiry\s*date\s*:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", t, flags=re.IGNORECASE)
            gen_true = re.search(r"generate\s+(an\s+)?image", lt) is not None and not re.search(
                r"do\s+not\s+generate", lt
            )
            if qty_m:
                entities["quantity_kg"] = float(qty_m.group(1))
            if price_m:
                entities["price_per_unit"] = float(price_m.group(1))
            if pname_m:
                entities["product_name"] = pname_m.group(1).strip()
            if avail_m:
                entities["available_date"] = avail_m.group(1)
            if exp_m:
                entities["expiry_date"] = exp_m.group(1)
            if gen_true:
                entities["generate_image"] = True
            return {"intent": "add_inventory", "entities": entities}

        # Schedule heuristics: detect delivery schedule queries and resolve common ranges
        if any(k in lt for k in ["schedule", "delivery schedule", "deliveries", "delivery plan"]):
            start_date: str | None = None
            end_date: str | None = None
            today = dt.date.today()
            # Compute current week Mon-Sun
            cur_mon = today - dt.timedelta(days=today.weekday())
            cur_sun = cur_mon + dt.timedelta(days=6)
            if "next week" in lt:
                nxt_mon = cur_mon + dt.timedelta(days=7)
                nxt_sun = nxt_mon + dt.timedelta(days=6)
                start_date, end_date = nxt_mon.isoformat(), nxt_sun.isoformat()
            elif any(k in lt for k in ["this week", "current week", "week"]) and "next" not in lt:
                start_date, end_date = cur_mon.isoformat(), cur_sun.isoformat()
            elif "today" in lt:
                start_date = end_date = today.isoformat()
            elif "tomorrow" in lt:
                tmr = today + dt.timedelta(days=1)
                start_date = end_date = tmr.isoformat()

            if start_date and end_date:
                entities["start_date"] = start_date
                entities["end_date"] = end_date
            return {"intent": "check_schedule", "entities": entities}

        # Flash-sale / expiring inventory heuristics
        if (
            any(k in lt for k in ["expiring", "expires", "going bad", "near expiry", "close to expiry", "flash sale", "discount"])
            and "add inventory" not in lt
            and "available date" not in lt
        ):
            # Extract days window if user mentions it
            m = re.search(r"(\d{1,2})\s*day", lt)
            if m:
                try:
                    entities["days"] = int(m.group(1))
                except Exception:
                    pass
            return {"intent": "flash_sale_check", "entities": entities}

        # Customer orders heuristics
        if any(k in lt for k in ["my orders", "orders i have", "order history", "orders i've", "orders i placed", "what orders", "show my orders"]):
            # Reuse week parsing similar to schedule
            start_date: str | None = None
            end_date: str | None = None
            today = dt.date.today()
            cur_mon = today - dt.timedelta(days=today.weekday())
            cur_sun = cur_mon + dt.timedelta(days=6)
            if "next week" in lt:
                nxt_mon = cur_mon + dt.timedelta(days=7)
                nxt_sun = nxt_mon + dt.timedelta(days=6)
                start_date, end_date = nxt_mon.isoformat(), nxt_sun.isoformat()
            elif any(k in lt for k in ["this week", "current week", "week"]) and "next" not in lt:
                start_date, end_date = cur_mon.isoformat(), cur_sun.isoformat()
            elif "today" in lt:
                start_date = end_date = today.isoformat()
            elif "tomorrow" in lt:
                tmr = today + dt.timedelta(days=1)
                start_date = end_date = tmr.isoformat()
            if start_date and end_date:
                entities["start_date"] = start_date
                entities["end_date"] = end_date
            return {"intent": "check_customer_orders", "entities": entities}

        # Knowledge/RAG heuristics: storage, nutrition, recipes, selection, seasonality (EN + basic Amharic cues)
        knowledge_tokens_en = [
            "store", "storage", "keep", "keep fresh", "refrigerate", "fridge", "ripe", "ripen",
            "nutrition", "nutritional", "vitamin", "protein", "calories",
            "recipe", "recipes", "cook", "cooking",
            "selection", "choose", "pick",
            "seasonality", "in season", "seasonal",
            "how should i", "how do i", "best way to",
        ]
        knowledge_tokens_am = [
            "ፍሪጅ",  # fridge
            "ማከማቻ",  # storage
            "እንዴት",   # how
            "የምግብ ንጥረ ነገር",  # nutrition (broad)
            "አብራሪ",  # recipe (approx)
            "ወቅታዊ",  # seasonal
        ]
        if any(tok in lt for tok in knowledge_tokens_en) or any(tok in (text or "") for tok in knowledge_tokens_am):
            return {"intent": "knowledge_query", "entities": entities}

        # Image generation heuristics: generate image/photo/picture (EN + Amharic cues)
        image_tokens_en = [
            "generate image", "generate a image", "generate a photo", "generate photo",
            "image of", "photo of", "picture of", "create image", "make an image", "render",
            "image", "photo", "picture",
        ]
        image_tokens_am = [
            "ምስል",  # image
            "ፎቶ",   # photo
            "ስእል",  # picture/image
        ]
        if any(tok in lt for tok in image_tokens_en) or any(tok in (text or "") for tok in image_tokens_am):
            return {"intent": "image_generation", "entities": entities}

        # 2) LLM-based detection (may be unavailable without network)
        prompt = (
            "You are an intent classifier for a horticulture marketplace chatbot.\n"
            "Classify the user's latest message into ONE of the following intents exactly:\n"
            f"{', '.join(INTENTS)}\n\n"
            "Also extract simple entities if present: product_name(s), quantity_kg (numeric), dates, location, phone (phone number), name, and delivery_location.\n"
            "Respond ONLY as compact JSON with keys 'intent' and 'entities'. Do not add explanations.\n\n"
            f"User message: {text}"
        )
        try:
            resp = self.model.generate_content(prompt)
            raw = getattr(resp, "text", "") or ""
            # Strip code fences if present
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.strip("`\n")
                if raw.lower().startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            intent = data.get("intent")
            if intent not in INTENTS:
                intent = "general_chat"
            ents = data.get("entities") or {}
            # Normalize possible variant keys to canonical names
            phone2 = ents.get("phone") or ents.get("phone_number") or ents.get("phoneNumber")
            if phone2 and "phone" not in entities:
                entities["phone"] = str(phone2)
            if ents.get("name"):
                entities.setdefault("name", ents.get("name"))
            if ents.get("location") or ents.get("delivery_location"):
                entities.setdefault("location", ents.get("location") or ents.get("delivery_location"))
            # Carry over other useful entities untouched
            for k in ("product_name", "product_names", "quantity_kg", "dates"):
                if k in ents and k not in entities:
                    entities[k] = ents[k]
            return {"intent": intent, "entities": entities}
        except Exception:
            # Fallback minimal structure retaining rule-extracted entities
            return {"intent": "general_chat", "entities": entities}


_PHONE_PATTERNS = [
    re.compile(r"\b(?:\+?251[-\s]?)?0?9\d{8}\b"),  # +2519XXXXXXXX or 09XXXXXXXX or 9XXXXXXXX
]


def _extract_phone(text: str) -> str | None:
    s = text or ""
    for pat in _PHONE_PATTERNS:
        m = pat.search(s)
        if m:
            return m.group(0).replace(" ", "").replace("-", "")
    return None


def _extract_name(text: str) -> str | None:
    # Patterns: "my name is Abebe", "name: Abebe"
    m = re.search(r"(?i)(?:my\s+name\s+is|name\s*:)\s*([A-Za-z\u1200-\u137F'\- ]{2,})", text or "")
    return m.group(1).strip() if m else None


def _extract_location(text: str) -> str | None:
    # Patterns: "location Addis Ababa", "location: Addis Ababa", "in Addis Ababa"
    s = text or ""
    m = re.search(r"(?i)location\s*:?[\s]+([A-Za-z\u1200-\u137F'\- ]{2,})", s)
    if m:
        return m.group(1).strip()
    m = re.search(r"(?i)\b(?:in|at)\s+([A-Za-z\u1200-\u137F'\- ]{2,})", s)
    return m.group(1).strip() if m else None
