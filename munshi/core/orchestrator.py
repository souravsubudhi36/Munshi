"""Orchestrator — central conversation state machine for Munshi.

Flow per turn:
  transcript → Claude API (with tools) → execute tools → spoken response
  Fallback: offline NLP → direct service calls → spoken response
"""

from __future__ import annotations

import asyncio
import json
from datetime import date

from loguru import logger

from munshi.ai.claude_client import ClaudeClient, ToolCall
from munshi.ai.offline_nlp import classify_intent
from munshi.ai.prompt_templates import ERROR_MESSAGES
from munshi.audio.audio_manager import AudioManager
from munshi.config import settings
from munshi.core import response_builder as rb
from munshi.core.session import Session
from munshi.db.database import get_session
from munshi.modules.inventory.schemas import StockUpdateInput
from munshi.modules.inventory.service import InventoryService
from munshi.modules.ledger.schemas import ExpenseInput, SaleInput
from munshi.modules.ledger.service import LedgerService
from munshi.modules.udhar.schemas import CreditInput, NewCustomerInput, PaymentInput
from munshi.modules.udhar.service import AmbiguousCustomerError, UdharService

# Shop ID 1 is the default single-shop configuration
DEFAULT_SHOP_ID = 1


class Orchestrator:
    """Main conversation loop — processes voice turns end-to-end."""

    def __init__(self) -> None:
        self.audio = AudioManager()
        self.claude = ClaudeClient()
        self.session: Session | None = None

    async def run(self) -> None:
        """Main loop — listen → understand → respond, forever."""
        await self.audio.start()
        logger.info("Orchestrator running. Waiting for wake word...")

        while True:
            try:
                await self._handle_turn()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Orchestrator error: {e}")
                await self.audio.speak(ERROR_MESSAGES["general_error"])

    async def _handle_turn(self) -> None:
        """Process one complete voice turn."""
        # Wait for wake word and capture utterance
        transcript = await self.audio.listen_and_transcribe()
        if not transcript:
            return

        logger.info(f"Transcript: '{transcript}'")

        # Start or continue session
        if not self.session:
            self.session = Session(shop_id=DEFAULT_SHOP_ID)
            logger.debug(f"New session: {self.session.session_id}")

        self.session.next_turn()

        # Handle pending disambiguation
        if self.session.awaiting_disambiguation:
            response = await self._resolve_disambiguation(transcript)
            await self.audio.speak(response)
            return

        # Handle pending confirmation
        if self.session.awaiting_confirmation:
            response = await self._resolve_confirmation(transcript)
            await self.audio.speak(response)
            return

        # Normal turn: send to Claude
        response_text, tool_calls = await self.claude.process(transcript)

        if tool_calls:
            # Execute all tool calls and build spoken response
            spoken = await self._execute_tools(tool_calls)
        elif response_text:
            spoken = response_text
        else:
            # Claude offline or no response → try offline NLP
            spoken = await self._handle_offline(transcript)

        if spoken:
            await self.audio.speak(spoken)

        # End session after a period of silence (simple: just reset after each turn)
        # In production: use a timer to keep session alive for follow-up questions
        # self.session = None  # Uncomment to reset after every turn

    async def _execute_tools(self, tool_calls: list[ToolCall]) -> str:
        """Execute tool calls against business services and return spoken response."""
        tool_results = []

        async with get_session() as db:
            ledger_svc = LedgerService(db, DEFAULT_SHOP_ID)
            udhar_svc = UdharService(db, DEFAULT_SHOP_ID)
            inventory_svc = InventoryService(db, DEFAULT_SHOP_ID)

            for call in tool_calls:
                result_content = await self._dispatch_tool(
                    call, ledger_svc, udhar_svc, inventory_svc
                )
                tool_results.append({
                    "tool_use_id": call.tool_use_id,
                    "content": json.dumps(result_content, ensure_ascii=False),
                })

        if not tool_results:
            return ERROR_MESSAGES["general_error"]

        # Send results back to Claude for final spoken response
        spoken = await self.claude.send_tool_results(tool_results)
        return spoken or ERROR_MESSAGES["general_error"]

    async def _dispatch_tool(
        self,
        call: ToolCall,
        ledger: LedgerService,
        udhar: UdharService,
        inventory: InventoryService,
    ) -> dict:
        try:
            if call.name == "add_sale":
                result = await ledger.add_sale(SaleInput(**call.inputs))
                return {"ok": True, "entry_id": result.id, "amount": result.amount}

            elif call.name == "add_expense":
                result = await ledger.add_expense(ExpenseInput(**call.inputs))
                return {"ok": True, "entry_id": result.id, "amount": result.amount}

            elif call.name == "get_daily_summary":
                target_date = None
                if "date" in call.inputs:
                    target_date = date.fromisoformat(call.inputs["date"])
                summary = await ledger.daily_summary(target_date)
                return {
                    "ok": True,
                    "date": str(summary.date),
                    "total_sales": summary.total_sales,
                    "total_expenses": summary.total_expenses,
                    "net_profit": summary.net_profit,
                    "count": summary.transaction_count,
                }

            elif call.name == "add_udhar":
                txn, customer = await udhar.add_credit(
                    CreditInput(
                        customer_name=call.inputs["customer_name"],
                        amount=call.inputs["amount"],
                        description=call.inputs.get("description"),
                    )
                )
                return {
                    "ok": True,
                    "customer": customer.name,
                    "amount": txn.amount,
                    "outstanding": customer.outstanding_amount,
                }

            elif call.name == "record_payment":
                txn, customer = await udhar.record_payment(
                    PaymentInput(
                        customer_name=call.inputs["customer_name"],
                        amount=call.inputs["amount"],
                    )
                )
                return {
                    "ok": True,
                    "customer": customer.name,
                    "amount": txn.amount,
                    "remaining": customer.outstanding_amount,
                }

            elif call.name == "get_outstanding":
                customer_name = call.inputs.get("customer_name")
                results = await udhar.get_outstanding(customer_name or None)
                return {
                    "ok": True,
                    "results": [
                        {
                            "customer": r.customer_name,
                            "outstanding": r.outstanding_amount,
                            "phone": r.phone,
                        }
                        for r in results
                    ],
                }

            elif call.name == "find_product_location":
                loc = await inventory.find_location(call.inputs["product_name"])
                return {
                    "ok": True,
                    "product": loc.product_name,
                    "location": loc.location_notes or loc.shelf_location or "not set",
                    "stock": loc.stock_quantity,
                }

            elif call.name == "check_stock":
                result = await inventory.check_stock(call.inputs["product_name"])
                return {
                    "ok": True,
                    "product": result.product_name,
                    "stock": result.stock_quantity,
                }

            elif call.name == "update_stock":
                result = await inventory.update_stock(
                    StockUpdateInput(
                        product_name=call.inputs["product_name"],
                        quantity=call.inputs["quantity"],
                        movement_type=call.inputs.get("movement_type", "purchase"),
                    )
                )
                return {"ok": True, "product": result.name, "new_stock": result.stock_quantity}

            elif call.name == "create_customer":
                customer = await udhar.create_customer(
                    NewCustomerInput(
                        name=call.inputs["name"],
                        phone=call.inputs.get("phone"),
                        aliases=call.inputs.get("aliases", []),
                    )
                )
                return {"ok": True, "customer_id": customer.id, "name": customer.name}

            else:
                return {"ok": False, "error": f"Unknown tool: {call.name}"}

        except AmbiguousCustomerError as e:
            if self.session:
                self.session.set_pending(
                    call.name, call.inputs,
                    needs_disambiguation=True, candidates=e.candidates
                )
            return {"ok": False, "error": "ambiguous_customer", "candidates": e.candidates}

        except ValueError as e:
            return {"ok": False, "error": str(e)}

        except Exception as e:
            logger.exception(f"Tool dispatch error ({call.name}): {e}")
            return {"ok": False, "error": "internal_error"}

    async def _resolve_disambiguation(self, transcript: str) -> str:
        """User is answering an ambiguity question — figure out which customer they meant."""
        if not self.session:
            return ERROR_MESSAGES["general_error"]

        candidates = self.session.disambiguation_candidates
        transcript_lower = transcript.lower()

        # Try to match user's answer to a candidate
        chosen = None
        for candidate in candidates:
            if candidate.lower() in transcript_lower:
                chosen = candidate
                break

        if not chosen:
            return rb.error_not_understood()

        # Replay the original action with the resolved customer name
        pending_action = self.session.pending_action
        pending_params = {**self.session.pending_params}
        pending_params["customer_name"] = chosen
        self.session.clear_pending()

        # Re-dispatch the tool with clarified params
        fake_call = ToolCall(pending_action, pending_params, "disambiguated")
        async with get_session() as db:
            ledger = LedgerService(db, DEFAULT_SHOP_ID)
            udhar = UdharService(db, DEFAULT_SHOP_ID)
            inventory = InventoryService(db, DEFAULT_SHOP_ID)
            result = await self._dispatch_tool(fake_call, ledger, udhar, inventory)

        if result.get("ok"):
            return await self.claude.send_tool_results([{
                "tool_use_id": "disambiguated",
                "content": json.dumps(result, ensure_ascii=False),
            }])
        return ERROR_MESSAGES["general_error"]

    async def _resolve_confirmation(self, transcript: str) -> str:
        """User is answering a confirmation question (haan/nahi)."""
        if not self.session:
            return ERROR_MESSAGES["general_error"]

        yes_words = {"haan", "ha", "yes", "bilkul", "theek", "kar do", "ok"}
        no_words = {"nahi", "nai", "no", "mat", "band karo", "cancel"}

        words = set(transcript.lower().split())
        if words & yes_words:
            pending_action = self.session.pending_action
            pending_params = self.session.pending_params
            self.session.clear_pending()
            fake_call = ToolCall(pending_action, pending_params, "confirmed")
            async with get_session() as db:
                result = await self._dispatch_tool(
                    fake_call,
                    LedgerService(db, DEFAULT_SHOP_ID),
                    UdharService(db, DEFAULT_SHOP_ID),
                    InventoryService(db, DEFAULT_SHOP_ID),
                )
            if result.get("ok"):
                return await self.claude.send_tool_results([{
                    "tool_use_id": "confirmed",
                    "content": json.dumps(result, ensure_ascii=False),
                }])
            return ERROR_MESSAGES["general_error"]
        elif words & no_words:
            self.session.clear_pending()
            return "Theek hai, cancel kar diya."
        else:
            return "Haan ya nahi bolo."

    async def _handle_offline(self, transcript: str) -> str:
        """Offline intent classification when Claude is unavailable."""
        intent = classify_intent(transcript)
        logger.info(f"Offline intent: {intent.name} ({intent.confidence:.2f})")

        if intent.name == "unknown" or intent.confidence < 0.3:
            return ERROR_MESSAGES["not_understood"]

        if intent.name == "get_daily_summary":
            async with get_session() as db:
                svc = LedgerService(db, DEFAULT_SHOP_ID)
                summary = await svc.daily_summary()
            return rb.daily_summary(
                summary.total_sales, summary.total_expenses,
                summary.net_profit, summary.transaction_count
            )

        if intent.name == "add_sale" and intent.params.get("amount"):
            async with get_session() as db:
                svc = LedgerService(db, DEFAULT_SHOP_ID)
                entry = await svc.add_sale(SaleInput(amount=intent.params["amount"]))
            return rb.sale_confirmed(entry.amount)

        # For more complex offline intents, ask user to repeat when online
        return "Internet nahi hai. Thodi der mein phir try karo."
