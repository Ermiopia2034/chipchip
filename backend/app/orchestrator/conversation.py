from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from app.orchestrator.session_manager import SessionManager
from app.orchestrator.tool_registry import ToolRegistry
from app.models.state_machine import StateMachine, States
from app.services.llm_service import LLMService, _tool_declarations
from app.services.db_service import DatabaseService


class ConversationOrchestrator:
    def __init__(self,
                 sessions: Optional[SessionManager] = None,
                 tools: Optional[ToolRegistry] = None,
                 llm: Optional[LLMService] = None,
                 db: Optional[DatabaseService] = None) -> None:
        self.sessions = sessions or SessionManager()
        self.tools = tools or ToolRegistry()
        self.llm = llm or LLMService()
        self.db = db or DatabaseService()

    async def process_message(self, session_id: str, user_message: str) -> Dict[str, Any]:
        logger = logging.getLogger(__name__)
        # 1. Load session + history
        session = await self.sessions.get_session(session_id)
        if not session:
            # Create if missing
            await self.sessions.create_session()
            session = await self.sessions.get_session(session_id)

        await self.sessions.add_message(session_id, "user", user_message)

        # Build state machine from session context
        current_flow = (session.get("context") or {}).get("current_flow") or States.IDLE
        sm = StateMachine(current_flow)

        # Directly route to the main LLM for intent discovery, tool calls, and response finalization.
        return await self._llm_direct_flow(session_id, session, user_message)

        # 2a. If we're mid-registration and the user sent a phone number, fast-path registration
        if sm.state == States.REGISTERING:
            phone = _extract_phone(user_message)
            if phone:
                last_intent = (session.get("context") or {}).get("last_intent") or "registration_customer"
                entities = {"phone": phone}
                return await self._handle_registration(session_id, session, last_intent, entities)

        # 2b. Detect intent (LLM with light heuristics)
        intent_res = self.detector.detect(user_message)
        intent = intent_res.get("intent") or "general_chat"
        entities = intent_res.get("entities") or {}
        try:
            logger.info("MSG session=%s intent=%s text_len=%d", session_id, intent, len(user_message))
        except Exception:
            pass

        # Update flow based on intent
        next_state = self._state_for_intent(intent)
        if next_state and sm.can_transition(next_state):
            sm.transition(next_state)
        # Save state
        context = session.get("context") or {}
        context["current_flow"] = sm.state
        context["last_intent"] = intent
        await self.sessions.update_session(session_id, {"context": context})

        # Handle special flows that are orchestrator-level (registration)
        if intent in ("registration_customer", "registration_supplier"):
            return await self._handle_registration(session_id, session, intent, entities)

        # Deterministic tool routing for intents that map 1:1 to a tool
        # Knowledge queries should hit RAG directly, then let LLM finalize using the tool result as context
        if intent == "knowledge_query":
            tool_args: Dict[str, Any] = {"query": user_message}
            tool_result = await self.tools.rag_query_handler(tool_args, session_id=session_id)
            tool_msg = tool_result.get("message", "")
            # Build a finalization prompt that embeds the tool context, and allow tools if LLM needs them
            try:
                session2 = await self.sessions.get_session(session_id) or session
                # Compose a context block instead of adding a visible assistant/tool message
                context_block = (
                    "Retrieved knowledge (context):\n" + tool_msg + "\n\n" +
                    "Please produce a concise, user-facing answer to the last user question. "
                    "Do not include metadata labels or list multiple bullets unless clearly relevant."
                )
                messages2 = self._build_messages(session2, context_block)
                tool_decls = _tool_declarations()
                final = self.llm.chat(messages2, tools=tool_decls, allow_tools=True)
                if final.get("type") == "tool_call":
                    # Execute once and finalize
                    name = final.get("name")
                    args = final.get("arguments") or {}
                    tool_res2 = await self.tools.execute(name, args, session_id=session_id)
                    # Ask the model to finalize based on the new tool output
                    context_block2 = (
                        "Additional tool result (context):\n" + (tool_res2.get("message", "")) + "\n\n" +
                        "Now provide the final concise answer to the user's question."
                    )
                    messages3 = self._build_messages(await self.sessions.get_session(session_id) or session2, context_block2)
                    final2 = self.llm.chat(messages3, tools=tool_decls, allow_tools=True)
                    if final2.get("type") == "text" and (final2.get("content") or "").strip():
                        out2 = final2.get("content", "")
                        await self.sessions.add_message(session_id, "assistant", out2)
                        return {"type": "text", "content": out2, "metadata": {"intent": intent}}
                    # Fallback to tool message if still not text
                    msg2 = tool_res2.get("message", "") or tool_msg
                    await self.sessions.add_message(session_id, "assistant", msg2)
                    return {"type": "text", "content": msg2, "metadata": {"intent": intent}}
                # Plain text from finalization
                if final.get("type") == "text" and (final.get("content") or "").strip():
                    out = final.get("content", "")
                    await self.sessions.add_message(session_id, "assistant", out)
                    return {"type": "text", "content": out, "metadata": {"intent": intent}}
            except Exception:
                pass
            # Fallback to grounded tool message
            await self.sessions.add_message(session_id, "assistant", tool_msg)
            return {"type": "text", "content": tool_msg, "metadata": {"intent": intent}}

        # Deterministic image generation routing
        if intent == "image_generation":
            # Try to extract a product name implicitly via tool's inference by passing the raw query
            tool_result = await self.tools.generate_product_image_handler({"query": user_message}, session_id=session_id)
            msg = tool_result.get("message", "")
            data = tool_result.get("data") or {}
            url = (data or {}).get("image_url") if isinstance(data, dict) else None
            # Persist a short caption in history for continuity
            await self.sessions.add_message(session_id, "assistant", msg)
            if isinstance(url, str) and url:
                # Send explicit image payload so the UI renders an image bubble
                return {"type": "image", "content": msg, "data": {"url": url}, "metadata": {"intent": intent}}
            # Fallback to text if URL missing
            return {"type": "text", "content": msg, "metadata": {"intent": intent}}

        if intent == "check_stock":
            tool_result = await self.tools.check_supplier_stock_handler({}, session_id=session_id)
            msg = tool_result.get("message", "")
            await self.sessions.add_message(session_id, "assistant", msg)
            return {"type": "text", "content": msg, "metadata": {"intent": intent}}
        if intent == "check_schedule":
            # Optional: accept date range via entities in future. Use defaults now.
            tool_args: Dict[str, Any] = {}
            # If intent detector provided dates, pass them
            if entities.get("start_date") and entities.get("end_date"):
                tool_args = {"start_date": entities.get("start_date"), "end_date": entities.get("end_date")}
            tool_result = await self.tools.get_supplier_schedule_handler(tool_args, session_id=session_id)
            msg = tool_result.get("message", "")
            await self.sessions.add_message(session_id, "assistant", msg)
            return {"type": "text", "content": msg, "metadata": {"intent": intent}}
        if intent == "flash_sale_check":
            # Pass days_threshold if the user specified a window
            tool_args: Dict[str, Any] = {}
            if entities.get("days"):
                tool_args["days_threshold"] = int(entities["days"])  # type: ignore[arg-type]
            tool_result = await self.tools.suggest_flash_sale_handler(tool_args, session_id=session_id)
            msg = tool_result.get("message", "")
            await self.sessions.add_message(session_id, "assistant", msg)
            return {"type": "text", "content": msg, "metadata": {"intent": intent}}
        if intent == "add_inventory":
            # If we have structured entities, call tool directly; otherwise continue normal LLM flow
            required = ("product_name", "quantity_kg", "price_per_unit", "available_date")
            if all(k in entities for k in required):
                args = {
                    "product_name": entities.get("product_name"),
                    "quantity_kg": entities.get("quantity_kg"),
                    "price_per_unit": entities.get("price_per_unit"),
                    "available_date": entities.get("available_date"),
                }
                if entities.get("expiry_date"):
                    args["expiry_date"] = entities.get("expiry_date")
                if "generate_image" in entities:
                    args["generate_image"] = bool(entities.get("generate_image"))
                tool_result = await self.tools.add_inventory_handler(args, session_id=session_id)
                msg = tool_result.get("message", "")
                await self.sessions.add_message(session_id, "assistant", msg)
                return {"type": "text", "content": msg, "metadata": {"intent": intent}}
        if intent == "check_customer_orders":
            tool_args: Dict[str, Any] = {}
            if entities.get("start_date") and entities.get("end_date"):
                tool_args["start_date"] = entities["start_date"]
                tool_args["end_date"] = entities["end_date"]
            if entities.get("status"):
                tool_args["status"] = entities["status"]
            tool_result = await self.tools.get_customer_orders_handler(tool_args, session_id=session_id)
            msg = tool_result.get("message", "")
            await self.sessions.add_message(session_id, "assistant", msg)
            return {"type": "text", "content": msg, "metadata": {"intent": intent}}

        # 4. Build LLM context and tool declarations
        tool_decls = _tool_declarations()
        messages = self._build_messages(session, user_message)

        # 5. Call LLM + function-calling loop
        result = self.llm.chat(messages, tools=tool_decls)
        # Single follow-up iteration if it returns tool call
        if result.get("type") == "tool_call":
            name = result.get("name")
            args = result.get("arguments") or {}
            try:
                logger.info("EXEC tool=%s session=%s", name, session_id)
            except Exception:
                pass
            tool_result = await self.tools.execute(name, args, session_id=session_id)
            # Append tool result and ask LLM to produce final answer
            await self.sessions.add_message(session_id, "assistant", f"TOOL {name} -> {tool_result.get('message')}")
            messages2 = self._build_messages(await self.sessions.get_session(session_id) or session, "Please finalize the response based on the tool result above.")
            final = self.llm.chat(messages2, tools=tool_decls)
            if final.get("type") == "text":
                await self.sessions.add_message(session_id, "assistant", final.get("content", ""))
                return {"type": "text", "content": final.get("content", ""), "metadata": {"intent": intent}}
            # Fallback if second call also returns a tool call: just return tool message
            await self.sessions.add_message(session_id, "assistant", tool_result.get("message", ""))
            return {"type": "text", "content": tool_result.get("message", ""), "metadata": {"intent": intent}}

        # If plain text reply
        if result.get("type") == "text":
            await self.sessions.add_message(session_id, "assistant", result.get("content", ""))
            return {"type": "text", "content": result.get("content", ""), "metadata": {"intent": intent}}

        # Last resort empty response
        await self.sessions.add_message(session_id, "assistant", "")
        return {"type": "text", "content": "", "metadata": {"intent": intent}}

    async def _handle_registration(self, session_id: str, session: Dict[str, Any], intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        user_type = "supplier" if intent == "registration_supplier" else "customer"
        name = entities.get("name") or session.get("name")
        phone = entities.get("phone") or session.get("phone")
        location = entities.get("location") or session.get("default_location")

        if not phone:
            msg = "Please provide your phone number to complete registration."
            await self.sessions.add_message(session_id, "assistant", msg)
            return {"type": "text", "content": msg}

        # Create user in DB and update session
        user_id = await self.db.create_user(phone, name, user_type, location)
        updates = {
            "user_id": user_id,
            "user_type": user_type,
            "registered": True,
            "phone": phone,
            "name": name,
            "default_location": location,
        }
        await self.sessions.update_session(session_id, updates)
        msg = f"Registration complete. Welcome {name or ''}! You are registered as a {user_type}."
        await self.sessions.add_message(session_id, "assistant", msg)
        return {"type": "text", "content": msg}

    def _state_for_intent(self, intent: str) -> Optional[str]:
        mapping = {
            "registration_customer": States.REGISTERING,
            "registration_supplier": States.REGISTERING,
            "place_order": States.ORDERING,
            "add_inventory": States.ADDING_INVENTORY,
            "product_inquiry": States.QUERYING,
            "knowledge_query": States.QUERYING,
            "image_generation": States.QUERYING,
            "check_stock": States.QUERYING,
            "check_schedule": States.QUERYING,
            "flash_sale_check": States.QUERYING,
            "general_chat": States.IDLE,
        }
        return mapping.get(intent)

    def _build_messages(self, session: Dict[str, Any], user_message: str) -> List[Dict[str, str]]:
        # Compose system-like preface
        user_type = session.get("user_type") or "unknown"
        registered = session.get("registered", False)
        name = session.get("name") or ""
        ctx = session.get("context") or {}
        context_summary = f"flow={ctx.get('current_flow')}, awaiting={ctx.get('awaiting_confirmation')}"
        preface = (
            "You are an Ethiopian horticulture marketplace assistant.\n\n"
            f"USER CONTEXT: user_type={user_type}, registered={registered}, name={name}\n"
            f"CURRENT STATE: {context_summary}\n"
            "Use available tools if needed. Keep responses concise.\n"
            "Date/time handling: Never ask the user for start/end dates. Resolve phrases like 'today', 'tomorrow', 'this week', 'next week' yourself using the get_current_time tool, and then call schedule/order tools with derived ISO dates. For supplier schedules, you may also call get_supplier_schedule without dates (defaults to current Mon–Sun).\n"
            "Expiry checks (suppliers): If asked about expiring items (e.g., 'in the next 3 days'), call suggest_flash_sale with days_threshold (default 3).\n"
        )
        history = session.get("conversation_history") or []
        messages: List[Dict[str, str]] = [{"role": "user", "content": preface}]
        for h in history[-10:]:
            role = h.get("role")
            content = h.get("content")
            if role in ("user", "assistant") and isinstance(content, str):
                # Map assistant to model role for Gemini
                r = "model" if role == "assistant" else "user"
                messages.append({"role": r, "content": content})
        messages.append({"role": "user", "content": user_message})
        return messages

    async def _llm_direct_flow(self, session_id: str, session: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        logger = logging.getLogger(__name__)
        tool_decls = _tool_declarations()
        messages = self._build_messages(session, user_message)
        last_tool_msg: str | None = None
        max_calls = 3
        for _ in range(max_calls):
            result = self.llm.chat(messages, tools=tool_decls, allow_tools=True)
            if result.get("type") == "tool_call":
                name = result.get("name")
                args = result.get("arguments") or {}
                try:
                    logger.info("EXEC tool=%s session=%s", name, session_id)
                except Exception:
                    pass
                tool_result = await self.tools.execute(name, args, session_id=session_id)
                # If this was the standalone image generation tool, return an explicit image payload for the UI
                if name == "generate_product_image":
                    try:
                        data = tool_result.get("data") if isinstance(tool_result, dict) else None
                        url = (data or {}).get("image_url") if isinstance(data, dict) else None
                        if isinstance(url, str) and url:
                            caption = tool_result.get("message", "")
                            await self.sessions.add_message(session_id, "assistant", caption)
                            return {"type": "image", "content": caption, "data": {"url": url}}
                    except Exception:
                        pass
                last_tool_msg = tool_result.get("message", "")
                context_block = (
                    "Tool result (context):\n" + (last_tool_msg or "") + "\n\n"
                    "Use this context to answer the user's last question concisely."
                )
                # Rebuild messages with the new context and continue loop
                messages = self._build_messages(await self.sessions.get_session(session_id) or session, context_block)
                continue
            if result.get("type") == "text":
                content = result.get("content", "")
                # If model returned empty text, attempt a no-tools finalization pass
                if not (content or "").strip():
                    try:
                        session2 = await self.sessions.get_session(session_id) or session
                        finalize_msg = (
                            "Finalize your answer to the user's last message now. "
                            "Provide a concise, helpful reply without calling tools."
                        )
                        final_messages = self._build_messages(session2, finalize_msg)
                        final_res = self.llm.chat(final_messages, tools=None, allow_tools=False)
                        if final_res.get("type") == "text":
                            final_text = final_res.get("content", "")
                            if (final_text or "").strip():
                                await self.sessions.add_message(session_id, "assistant", final_text)
                                return {"type": "text", "content": final_text}
                    except Exception:
                        pass
                    # Try another loop iteration allowing tools again
                    continue
                await self.sessions.add_message(session_id, "assistant", content)
                return {"type": "text", "content": content}
        # Fallbacks
        if last_tool_msg:
            await self.sessions.add_message(session_id, "assistant", last_tool_msg)
            return {"type": "text", "content": last_tool_msg}
        await self.sessions.add_message(session_id, "assistant", "")
        return {"type": "text", "content": ""}


def _extract_phone(text: str) -> str | None:
    # Ethiopian formats: 09XXXXXXXX, +2519XXXXXXXX, 2519XXXXXXXX (allow spaces/dashes)
    pat = re.compile(r"\b(?:\+?251[-\s]?)?0?9\d{8}\b")
    m = pat.search(text or "")
    return m.group(0).replace(" ", "").replace("-", "") if m else None
