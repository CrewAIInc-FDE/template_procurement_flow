import json
import os
import unittest
from unittest.mock import Mock, patch

from procurement_flow import main as flow_main
from procurement_flow.main import ProcurementFlow
from procurement_flow.procurement import (
    build_quote_review,
    generate_purchase_orders,
    parse_award_feedback,
    validate_awards,
)
from procurement_flow.tools import custom_tool
from procurement_flow.tools.custom_tool import extract_pdf_text
from procurement_flow.types import QuoteCollection, RequestDraft, RfqDispatch, ScreeningResult


class QuoteScoringTests(unittest.TestCase):
    def setUp(self):
        self.items = [
            {
                "request_item_id": 1,
                "catalog_item_id": "IT-001",
                "sku": "LAP-14",
                "name": "Laptop",
                "quantity": 2,
            }
        ]

    def test_usd_clp_scoring_ties_and_risks_do_not_change_score(self):
        quotes = [
            {
                "quote_id": "Q-A",
                "supplier_name": "Alpha",
                "request_item_id": 1,
                "unit_price": 95000,
                "currency": "CLP",
                "delivery_days": 2,
                "received_at": "2026-07-20T10:00:00Z",
                "message_id": "m-a",
                "risk_notes": ["Informational risk"],
            },
            {
                "quote_id": "Q-B",
                "supplier_name": "Beta",
                "request_item_id": 1,
                "unit_price": 110,
                "currency": "USD",
                "delivery_days": 1,
                "received_at": "2026-07-20T11:00:00Z",
                "message_id": "m-b",
            },
            {
                "quote_id": "Q-C",
                "supplier_name": "Gamma",
                "request_item_id": 1,
                "unit_price": 95000,
                "currency": "CLP",
                "delivery_days": 2,
                "received_at": "2026-07-20T12:00:00Z",
                "message_id": "m-c",
            },
        ]
        review = build_quote_review("PR-1001", self.items, quotes, 950)
        options = {option.quote_id: option for option in review.lines[0].options}

        self.assertEqual(options["Q-A"].line_total_usd, 200.0)
        self.assertEqual(options["Q-A"].price_score, 100.0)
        self.assertEqual(options["Q-A"].delivery_score, 50.0)
        self.assertEqual(options["Q-A"].total_score, 75.0)
        self.assertEqual(options["Q-B"].total_score, 95.5)
        self.assertTrue(options["Q-A"].is_cheapest)
        self.assertTrue(options["Q-C"].is_cheapest)
        self.assertTrue(options["Q-B"].is_fastest)
        self.assertEqual(review.lines[0].suggested_quote_id, "Q-B")

    def test_latest_supplier_revision_wins(self):
        base = {
            "supplier_name": "Alpha",
            "request_item_id": 1,
            "currency": "USD",
            "delivery_days": 3,
            "message_id": "m",
        }
        review = build_quote_review(
            "PR-1001",
            self.items,
            [
                {**base, "quote_id": "Q-OLD", "unit_price": 100, "received_at": "2026-07-19"},
                {**base, "quote_id": "Q-NEW", "unit_price": 90, "received_at": "2026-07-20"},
            ],
            950,
        )
        self.assertEqual([o.quote_id for o in review.lines[0].options], ["Q-NEW"])
        self.assertIn("Discarded older revision Q-OLD", review.warnings[0])

    def test_override_validation_and_plain_approval_defaults(self):
        review = build_quote_review(
            "PR-1001",
            self.items,
            [
                {"quote_id": "Q-A", "supplier_name": "Alpha", "request_item_id": 1,
                 "unit_price": 100, "currency": "USD", "delivery_days": 2,
                 "received_at": "2026-07-20", "message_id": "m-a"},
                {"quote_id": "Q-B", "supplier_name": "Beta", "request_item_id": 1,
                 "unit_price": 110, "currency": "USD", "delivery_days": 1,
                 "received_at": "2026-07-20", "message_id": "m-b"},
            ],
            950,
        )
        selected = validate_awards(review, [{"request_item_id": 1, "quote_id": "Q-A"}])
        self.assertEqual(selected[0].quote_id, "Q-A")
        with self.assertRaisesRegex(ValueError, "does not belong"):
            validate_awards(review, [{"request_item_id": 1, "quote_id": "unknown"}])
        with self.assertRaisesRegex(ValueError, "already awarded"):
            validate_awards(review, selected, [1])
        decision, defaults = parse_award_feedback("approved", review)
        self.assertEqual(decision, "approved")
        self.assertEqual(defaults[0].quote_id, review.lines[0].suggested_quote_id)

    def test_pdf_without_attachment_data_returns_warning(self):
        self.assertIn("WARNING", extract_pdf_text(json.dumps({"size": 0})))


class PurchaseOrderTests(unittest.TestCase):
    def _award(self, item_id, supplier_id, supplier_name, quote_id):
        return {
            "request_item_id": item_id,
            "catalog_item_id": f"IT-{item_id:03d}",
            "sku": f"SKU-{item_id}",
            "item_name": f"Item {item_id}",
            "quantity": 1,
            "quote_id": quote_id,
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "unit_price": 100,
            "currency": "USD",
            "line_total": 100,
            "line_total_usd": 100,
            "delivery_days": 2,
            "risk_notes": [],
        }

    def test_one_po_per_supplier_and_multiple_suppliers(self):
        docs = generate_purchase_orders(
            "PR-1001", [],
            [self._award(1, "S-1", "Alpha", "Q1"), self._award(2, "S-1", "Alpha", "Q2")],
            [], 950,
        )
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].po_number, "PO-1001-01")
        self.assertEqual(docs[0].item_ids, [1, 2])

        docs = generate_purchase_orders(
            "PR-1001", [],
            [self._award(1, "S-1", "Alpha", "Q1"), self._award(2, "S-2", "Beta", "Q2")],
            [], 950,
        )
        self.assertEqual([doc.po_number for doc in docs], ["PO-1001-01", "PO-1001-02"])

    def test_later_cycle_reuses_supplier_po_without_duplicate_item(self):
        existing = self._award(1, "S-1", "Alpha", "Q1")
        documents = generate_purchase_orders(
            "PR-1001",
            [existing],
            [self._award(2, "S-1", "Alpha", "Q2")],
            [{"supplier_id": "S-1", "po_number": "PO-1001-01"}],
            950,
        )
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].po_number, "PO-1001-01")
        self.assertEqual(documents[0].item_ids, [1, 2])


class FlowContractTests(unittest.TestCase):
    def test_flow_builds_and_missing_gmail_configuration_is_retryable(self):
        flow = ProcurementFlow()
        flow.state.clp_per_usd = 950
        flow.state.request = {
            "pr_number": "PR-1001",
            "line_items": [{"request_item_id": 1, "quantity": 1}],
        }
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("COMPOSIO_API_KEY", None)
            os.environ.pop("COMPOSIO_USER_ID", None)
            flow.run_quote_collection()
        flow.finish_no_quotes()
        self.assertEqual(flow.state.final_status, "awaiting_quotes")
        self.assertIn("Gmail is not configured", flow.state.warnings[0])

    def test_rejected_intake_never_sends_supplier_email(self):
        flow = ProcurementFlow()
        flow.state.request = {"pr_number": "PR-1001"}
        flow.state.catalog = [{
            "id": "IT-001", "sku": "LAP", "name": "Laptop",
            "unit_price_usd": 100, "category": "it_office",
        }]
        draft = RequestDraft(
            line_items=[{
                "catalog_item_id": "IT-001", "quantity": 1,
                "unit_price_usd": 0, "line_total_usd": 0,
            }],
            justification="Personal gift", urgency="normal", unmatched=[],
            estimated_total_usd=0, detected_language="en",
        )

        def reject():
            flow.state.screening = ScreeningResult(
                verdict="reject", violations=["Personal use"], anomalies=[], reasoning="Rejected",
            )

        llm = unittest.mock.Mock()
        llm.call.return_value = draft
        with patch.object(flow_main, "LLM", return_value=llm), \
             patch.object(flow, "_run_screening", side_effect=reject), \
             patch.object(flow, "_dispatch_rfq_emails") as send:
            flow.run_intake()
        send.assert_not_called()
        self.assertEqual(flow.state.final_status, "rejected")

    def test_demo_override_sends_to_one_address_and_reuses_sent_rfq(self):
        flow = ProcurementFlow()
        flow.state.request = {"pr_number": "PR-1001"}
        flow.state.request_draft = RequestDraft(
            line_items=[{
                "catalog_item_id": "IT-001", "sku": "LAP", "name": "Laptop",
                "quantity": 1, "unit_price_usd": 100, "line_total_usd": 100,
            }],
            justification="Work", urgency="normal", unmatched=[],
            estimated_total_usd=100, detected_language="en",
        )
        flow.state.catalog = [{"id": "IT-001", "category": "it_office"}]
        flow.state.suppliers = [{
            "id": "S-001", "name": "Supplier", "email": "quotes@supplier.example",
            "categories": ["it_office"],
        }]
        calls = []

        def action(name, **kwargs):
            calls.append((name, kwargs))
            if name == "GMAIL_FETCH_EMAILS":
                return {"messages": []}
            return {"id": "sent-1", "thread_id": "thread-1"}

        with patch.dict(os.environ, {
            "COMPOSIO_API_KEY": "key",
            "COMPOSIO_USER_ID": "procurement-demo",
            "DEMO_RFQ_RECIPIENT_OVERRIDE": "personal@example.com",
        }), patch.object(flow_main, "run_composio_action", side_effect=action):
            flow._dispatch_rfq_emails()

        self.assertEqual(flow.state.rfq_dispatches[0].actual_recipient, "personal@example.com")
        self.assertTrue(flow.state.rfq_dispatches[0].override_applied)
        self.assertEqual(calls[-1][0], "GMAIL_SEND_EMAIL")
        self.assertEqual(calls[-1][1]["recipient_email"], "personal@example.com")

        flow.state.rfq_dispatches = []
        with patch.dict(os.environ, {
            "COMPOSIO_API_KEY": "key",
            "COMPOSIO_USER_ID": "procurement-demo",
            "DEMO_RFQ_RECIPIENT_OVERRIDE": "personal@example.com",
        }), patch.object(
            flow_main, "run_composio_action",
            return_value={"messages": [{"id": "sent-1", "thread_id": "thread-1"}]},
        ) as existing:
            flow._dispatch_rfq_emails()
        self.assertEqual(existing.call_count, 1)
        self.assertEqual(flow.state.rfq_dispatches[0].gmail_thread_id, "thread-1")

    def test_composio_action_unwraps_data_and_surfaces_errors(self):
        client = Mock()
        client.tools.execute.return_value = {
            "successful": True,
            "data": {"id": "message-1"},
            "error": None,
        }
        with patch.dict(os.environ, {"COMPOSIO_USER_ID": "procurement-demo"}), \
             patch.object(custom_tool, "_composio", return_value=client):
            self.assertEqual(
                custom_tool.run_composio_action("GMAIL_SEND_EMAIL", body="hello"),
                {"id": "message-1"},
            )
            client.tools.execute.return_value = {
                "successful": False,
                "data": {},
                "error": "not connected",
            }
            with self.assertRaisesRegex(RuntimeError, "not connected"):
                custom_tool.run_composio_action("GMAIL_SEND_EMAIL", body="hello")

    def test_only_recorded_inbound_thread_can_become_a_quote(self):
        flow = ProcurementFlow()
        dispatch = RfqDispatch(
            rfq_id="RFQ-PR-1001-S-001", supplier_id="S-001", supplier_name="Supplier",
            actual_recipient="personal@example.com", gmail_message_id="outbound",
            gmail_thread_id="thread-1", status="sent",
        )
        flow.state.rfq_dispatches = [dispatch]
        self.assertEqual(
            flow_main.gmail_reply_query(dispatch),
            'in:inbox -from:me from:personal@example.com "RFQ-PR-1001-S-001"',
        )
        collection = QuoteCollection.model_validate({
            "replies": [
                {"rfq_id": dispatch.rfq_id, "message_id": "outbound", "thread_id": "thread-1", "sender": "personal@example.com", "label_ids": ["SENT"], "received_at": "2026-07-21"},
                {"rfq_id": dispatch.rfq_id, "message_id": "wrong", "thread_id": "thread-2", "sender": "personal@example.com", "label_ids": ["INBOX"], "received_at": "2026-07-21"},
                {"rfq_id": dispatch.rfq_id, "message_id": "spoof", "thread_id": "thread-1", "sender": "other@example.com", "label_ids": ["INBOX"], "received_at": "2026-07-21"},
                {"rfq_id": dispatch.rfq_id, "message_id": "reply-1", "thread_id": "thread-1", "sender": "Demo User <personal@example.com>", "label_ids": ["INBOX"], "received_at": "2026-07-21"},
            ],
            "quotes": [{
                "rfq_id": dispatch.rfq_id, "thread_id": "thread-1", "quote_id": "Q-1",
                "supplier_name": "From spoof", "request_item_id": 1, "unit_price": 100,
                "currency": "USD", "delivery_days": 2, "received_at": "2026-07-21",
                "message_id": "reply-1",
            }],
        })
        sanitized = flow._sanitize_quote_collection(collection)
        self.assertEqual([reply.message_id for reply in sanitized.replies], ["reply-1"])
        self.assertEqual(sanitized.quotes[0].supplier_id, "S-001")
        self.assertEqual(sanitized.quotes[0].supplier_name, "Supplier")


if __name__ == "__main__":
    unittest.main()
