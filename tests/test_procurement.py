import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pdfplumber
from reportlab.pdfgen import canvas

from procurement_flow import main as flow_main
from procurement_flow.crews.intake_crew.intake_crew import ProcurementIntakeCrew
from procurement_flow.crews.quote_review_crew.quote_review_crew import QuoteReviewCrew
from procurement_flow.main import ProcurementFlow
from procurement_flow.procurement import (
    build_quote_review,
    generate_purchase_orders,
    parse_award_feedback,
    render_purchase_order_pdf,
    validate_awards,
)
from procurement_flow.tools import gmail_tools
from procurement_flow.tools.gmail_tools import extract_pdf_text
from procurement_flow.types import (
    QuoteCollection,
    RfqDispatch,
    ScreeningResult,
    SourcingPlan,
)


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

    def test_downloaded_pdf_attachment_is_extracted(self):
        with tempfile.TemporaryDirectory(prefix="procurement-quote-") as temp_dir:
            pdf_path = Path(temp_dir) / "quote.pdf"
            document = canvas.Canvas(str(pdf_path))
            document.drawString(72, 720, "Unit price USD 100")
            document.save()

            text = extract_pdf_text(
                json.dumps({"attachment": {"file_path": str(pdf_path)}}),
                temp_dir,
            )

        self.assertIn("Unit price USD 100", text)

    def test_composio_pdf_object_is_downloaded_and_extracted(self):
        with tempfile.TemporaryDirectory(prefix="procurement-quote-") as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            document = canvas.Canvas(str(source_path))
            document.drawString(72, 720, "Delivery 14 days")
            document.save()
            response = Mock(status_code=200)
            response.iter_content.return_value = [source_path.read_bytes()]
            payload = json.dumps({
                "attachment": {
                    "name": "quote.pdf",
                    "mimetype": "application/pdf",
                    "s3url": "https://files.example/quote.pdf",
                }
            })

            with patch.dict(os.environ, {"COMPOSIO_CACHE_DIR": temp_dir}), patch(
                "composio.core.models._files.requests.get", return_value=response
            ):
                text = extract_pdf_text(payload, temp_dir)

        self.assertIn("Delivery 14 days", text)

    def test_incomplete_quote_line_becomes_a_warning(self):
        review = build_quote_review(
            "PR-1001",
            self.items,
            [{
                "quote_id": "incomplete",
                "supplier_name": "Alpha",
                "request_item_id": 1,
                "unit_price": None,
                "currency": "USD",
                "delivery_days": None,
                "received_at": "2026-07-23T10:00:00Z",
                "message_id": "reply-1",
            }],
            950,
        )

        self.assertEqual(review.lines, [])
        self.assertIn("unscorable", review.warnings[0])


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

    def test_vendor_ready_pdf_contains_only_its_purchase_order(self):
        documents = generate_purchase_orders(
            "PR-1001",
            [],
            [self._award(1, "S-1", "Alpha", "Q1")],
            [],
            950,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = render_purchase_order_pdf(
                documents[0], Path(temp_dir) / "PO-1001-01.pdf"
            )
            with pdfplumber.open(path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        self.assertIn("PURCHASE ORDER PO-1001-01", text)
        self.assertIn("Supplier: Alpha", text)
        self.assertIn("Item 1", text)
        self.assertNotIn("INTERNAL DRAFT", text)


class FlowContractTests(unittest.TestCase):
    def _intake_builder(
        self,
        *,
        override="personal@example.com",
        suppliers=None,
        dispatch_error="",
    ):
        catalog = [{
            "id": "IT-001",
            "sku": "LAP",
            "name": "Laptop",
            "unit_price_usd": 100,
            "category": "it_office",
        }]
        suppliers = suppliers or [{
            "id": "S-001",
            "name": "Supplier",
            "email": "quotes@supplier.example",
            "categories": ["it_office"],
        }]
        builder = ProcurementIntakeCrew(
            pr_number="PR-1001",
            catalog=catalog,
            suppliers=suppliers,
            override_recipient=override,
            dispatch_error=dispatch_error,
        )
        builder.crew()
        return builder

    def _plan(self, supplier_shortlist=None):
        return SourcingPlan.model_validate({
            "request_draft": {
                "line_items": [{
                    "catalog_item_id": "IT-001",
                    "quantity": 1,
                    "unit_price_usd": 0,
                    "line_total_usd": 0,
                }],
                "justification": "Work",
                "urgency": "normal",
                "unmatched": [],
                "estimated_total_usd": 0,
                "detected_language": "en",
            },
            "supplier_shortlist": supplier_shortlist or [{
                "supplier_id": "S-001",
                "catalog_item_ids": ["IT-001"],
            }],
        })

    @staticmethod
    def _output(model):
        return Mock(pydantic=model, raw=model.model_dump_json())

    @staticmethod
    def _tool_context(builder, name, tool_input, result=None):
        return SimpleNamespace(
            crew=builder._runtime_crew,
            task=builder.rfq_dispatch_task(),
            tool_name=name,
            tool_input=tool_input,
            tool_result=result,
        )

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

    def test_sourcing_plan_is_canonicalized(self):
        builder = self._intake_builder()
        valid, result = builder.validate_sourcing_plan(self._output(self._plan()))
        self.assertTrue(valid)
        plan = SourcingPlan.model_validate_json(result)
        line = plan.request_draft.line_items[0]
        self.assertEqual((line.sku, line.name), ("LAP", "Laptop"))
        self.assertEqual((line.unit_price_usd, line.line_total_usd), (100, 100))
        self.assertEqual(plan.request_draft.estimated_total_usd, 100)

    def test_sourcing_plan_rejects_unknown_or_incompatible_suppliers(self):
        suppliers = [
            {
                "id": "S-001", "name": "IT", "email": "it@example.com",
                "categories": ["it_office"],
            },
            {
                "id": "S-002", "name": "Safety", "email": "ppe@example.com",
                "categories": ["ppe_safety"],
            },
        ]
        for supplier_id, error in (
            ("S-999", "Unknown supplier"),
            ("S-002", "incompatible"),
        ):
            with self.subTest(supplier_id=supplier_id):
                builder = self._intake_builder(suppliers=suppliers)
                plan = self._plan([{
                    "supplier_id": supplier_id,
                    "catalog_item_ids": ["IT-001"],
                }])
                valid, message = builder.validate_sourcing_plan(self._output(plan))
                self.assertFalse(valid)
                self.assertIn(error, message)

    def test_rejected_intake_skips_conditional_gmail_task(self):
        builder = self._intake_builder()
        verdict = ScreeningResult(
            verdict="reject",
            violations=["Personal use"],
            anomalies=[],
            reasoning="Rejected",
        )
        task = builder.rfq_dispatch_task()
        self.assertFalse(task.should_execute(self._output(verdict)))
        self.assertFalse(task.reloaded)

    def test_same_recipient_reuses_id_only_sent_message(self):
        builder = self._intake_builder()
        builder.validate_sourcing_plan(self._output(self._plan()))
        rfq_id = "RFQ-PR-1001-S-001"
        fetch = self._tool_context(
            builder,
            "GMAIL_FETCH_EMAILS",
            {"query": rfq_id},
            json.dumps({"messages": [{"id": "existing-1"}]}),
        )
        self.assertIsNone(builder.guard_gmail_tool(fetch))
        self.assertEqual(
            fetch.tool_input["query"],
            f'in:sent to:personal@example.com "{rfq_id}"',
        )
        builder.capture_gmail_result(fetch)

        send = self._tool_context(
            builder,
            "GMAIL_SEND_EMAIL",
            {"subject": rfq_id},
        )
        self.assertFalse(builder.guard_gmail_tool(send))
        builder.validate_dispatch_batch(Mock())
        dispatch = builder.dispatch_batch.dispatches[0]
        self.assertEqual(dispatch.status, "sent")
        self.assertEqual(dispatch.gmail_message_id, "existing-1")
        self.assertEqual(dispatch.gmail_thread_id, "")

    def test_changed_recipient_allows_new_send_with_id_only_response(self):
        builder = self._intake_builder(override="buyer@proton.me")
        builder.validate_sourcing_plan(self._output(self._plan()))
        rfq_id = "RFQ-PR-1001-S-001"
        fetch = self._tool_context(
            builder,
            "GMAIL_FETCH_EMAILS",
            {"query": rfq_id},
            json.dumps({"messages": []}),
        )
        builder.guard_gmail_tool(fetch)
        self.assertIn("to:buyer@proton.me", fetch.tool_input["query"])
        builder.capture_gmail_result(fetch)

        send = self._tool_context(
            builder,
            "GMAIL_SEND_EMAIL",
            {"subject": rfq_id},
            json.dumps({"id": "sent-proton"}),
        )
        self.assertIsNone(builder.guard_gmail_tool(send))
        self.assertEqual(send.tool_input["recipient_email"], "buyer@proton.me")
        builder.capture_gmail_result(send)
        builder.validate_dispatch_batch(Mock())
        dispatch = builder.dispatch_batch.dispatches[0]
        self.assertEqual((dispatch.status, dispatch.gmail_message_id), ("sent", "sent-proton"))

    def test_missing_message_id_is_a_failed_dispatch(self):
        builder = self._intake_builder()
        builder.validate_sourcing_plan(self._output(self._plan()))
        rfq_id = "RFQ-PR-1001-S-001"
        fetch = self._tool_context(
            builder, "GMAIL_FETCH_EMAILS", {"query": rfq_id}, '{"messages":[]}'
        )
        builder.guard_gmail_tool(fetch)
        builder.capture_gmail_result(fetch)
        send = self._tool_context(
            builder, "GMAIL_SEND_EMAIL", {"subject": rfq_id}, "{}"
        )
        builder.guard_gmail_tool(send)
        builder.capture_gmail_result(send)
        builder.validate_dispatch_batch(Mock())
        dispatch = builder.dispatch_batch.dispatches[0]
        self.assertEqual(dispatch.status, "failed")
        self.assertIn("verifiable message ID", dispatch.error)
        self.assertIn("verifiable message ID", builder.dispatch_batch.warnings[0])

    def test_dispatch_guardrail_retries_missing_tool_steps(self):
        builder = self._intake_builder()
        builder.validate_sourcing_plan(self._output(self._plan()))
        valid, message = builder.validate_dispatch_batch(Mock())
        self.assertFalse(valid)
        self.assertIn("GMAIL_FETCH_EMAILS", message)

        rfq_id = "RFQ-PR-1001-S-001"
        fetch = self._tool_context(
            builder, "GMAIL_FETCH_EMAILS", {"query": rfq_id}, '{"messages":[]}'
        )
        builder.guard_gmail_tool(fetch)
        builder.capture_gmail_result(fetch)
        valid, message = builder.validate_dispatch_batch(Mock())
        self.assertFalse(valid)
        self.assertIn("GMAIL_SEND_EMAIL", message)

    def test_partial_dispatch_failure_preserves_success(self):
        suppliers = [
            {
                "id": "S-001", "name": "One", "email": "one@example.com",
                "categories": ["it_office"],
            },
            {
                "id": "S-002", "name": "Two", "email": "two@example.com",
                "categories": ["it_office"],
            },
        ]
        builder = self._intake_builder(suppliers=suppliers)
        plan = self._plan([
            {"supplier_id": supplier_id, "catalog_item_ids": ["IT-001"]}
            for supplier_id in ("S-001", "S-002")
        ])
        builder.validate_sourcing_plan(self._output(plan))
        for supplier_id, result in (("S-001", '{"id":"sent-1"}'), ("S-002", "{}")):
            rfq_id = f"RFQ-PR-1001-{supplier_id}"
            fetch = self._tool_context(
                builder, "GMAIL_FETCH_EMAILS", {"query": rfq_id}, '{"messages":[]}'
            )
            builder.guard_gmail_tool(fetch)
            builder.capture_gmail_result(fetch)
            send = self._tool_context(
                builder, "GMAIL_SEND_EMAIL", {"subject": rfq_id}, result
            )
            builder.guard_gmail_tool(send)
            builder.capture_gmail_result(send)
        builder.validate_dispatch_batch(Mock())
        self.assertEqual(
            [dispatch.status for dispatch in builder.dispatch_batch.dispatches],
            ["sent", "failed"],
        )
        self.assertEqual(len(builder.dispatch_batch.warnings), 1)

    def test_composio_action_unwraps_data_and_surfaces_errors(self):
        client = Mock()
        client.tools.execute.return_value = {
            "successful": True,
            "data": {"id": "message-1"},
            "error": None,
        }
        with patch.dict(os.environ, {"COMPOSIO_USER_ID": "procurement-demo"}), \
             patch.object(gmail_tools, "_composio", return_value=client):
            self.assertEqual(
                gmail_tools.run_composio_action("GMAIL_SEND_EMAIL", body="hello"),
                {"id": "message-1"},
            )
            client.tools.execute.return_value = {
                "successful": False,
                "data": {},
                "error": "not connected",
            }
            with self.assertRaisesRegex(RuntimeError, "not connected"):
                gmail_tools.run_composio_action("GMAIL_SEND_EMAIL", body="hello")

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
            'in:inbox from:personal@example.com "PR-1001" "S-001"',
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

    def test_quote_search_is_canonicalized_before_gmail_call(self):
        search = {
            "rfq_id": "RFQ-PR-1001-S-002",
            "supplier_id": "S-002",
            "query": 'in:inbox from:personal@example.com "PR-1001" "S-002"',
        }
        builder = QuoteReviewCrew(gmail_tools=[], searches=[search])
        task = builder.quote_extraction_task()
        context = SimpleNamespace(
            task=task,
            tool_name="Gmail Fetch Emails",
            tool_input={
                "query": 'in:inbox -from:me "RFQ\u2013PR\u20131001\u2013S\u2013002"',
                "page_token": "next-page",
            },
        )

        self.assertIsNone(builder.canonicalize_gmail_search(context))
        self.assertEqual(context.tool_input["query"], search["query"])
        self.assertEqual(context.tool_input["page_token"], "next-page")
        self.assertEqual(context.tool_input["max_results"], 100)

    def test_pdf_quote_guardrail_requires_attachment_read(self):
        collection = QuoteCollection.model_validate({
            "quotes": [{
                "quote_id": "quote.pdf",
                "supplier_name": "Supplier",
                "request_item_id": 1,
                "unit_price": 100,
                "currency": "USD",
                "delivery_days": 2,
                "received_at": "2026-07-23",
                "message_id": "reply-1",
                "source": "email",
            }]
        })
        builder = QuoteReviewCrew(gmail_tools=[], searches=[])
        builder.capture_pdf_tool_state(SimpleNamespace(
            tool_name="Gmail Fetch Emails",
            tool_input={},
            raw_tool_result={
                "messages": [{
                    "id": "reply-1",
                    "attachments": [{"filename": "quote.pdf"}],
                }]
            },
            tool_result=None,
        ))
        valid, message = builder.require_pdf_quote_details(self._output(collection))

        self.assertFalse(valid)
        self.assertIn("read_gmail_pdf_attachment", message)

        builder.capture_pdf_tool_state(SimpleNamespace(
            tool_name="read_gmail_pdf_attachment",
            tool_input={"message_id": "reply-1"},
            raw_tool_result="Extracted PDF quote text",
            tool_result=None,
        ))
        valid, _ = builder.require_pdf_quote_details(self._output(collection))
        self.assertTrue(valid)

    @staticmethod
    def _po_document():
        return generate_purchase_orders(
            "PR-1001",
            [],
            [{
                "request_item_id": 1,
                "catalog_item_id": "IT-001",
                "sku": "LAP",
                "item_name": "Laptop",
                "quantity": 1,
                "quote_id": "Q-1",
                "supplier_id": "S-001",
                "supplier_name": "Supplier",
                "unit_price": 100,
                "currency": "USD",
                "line_total": 100,
                "line_total_usd": 100,
                "delivery_days": 2,
                "risk_notes": [],
            }],
            [],
            950,
        )[0]

    @staticmethod
    def _po_rfq(recipient="personal@example.com"):
        return RfqDispatch(
            rfq_id="RFQ-PR-1001-S-001",
            supplier_id="S-001",
            supplier_name="Supplier",
            intended_recipient="quotes@supplier.example",
            actual_recipient=recipient,
            override_applied=True,
            gmail_message_id="rfq-1",
            status="sent",
        )

    def test_po_delivery_reuses_same_recipient_and_document(self):
        flow = ProcurementFlow()
        with tempfile.TemporaryDirectory(prefix="procurement-po-") as temp_dir, patch.object(
            flow_main,
            "run_composio_action",
            return_value={"messages": [{"id": "existing-po", "threadId": "thread-po"}]},
        ) as action:
            result = flow._dispatch_purchase_order(
                self._po_document(), self._po_rfq(), Mock(), Path(temp_dir)
            )
        self.assertEqual((result.status, result.gmail_message_id), ("sent", "existing-po"))
        self.assertTrue(result.reused)
        self.assertEqual(result.attempts, 0)
        query = action.call_args.kwargs["query"]
        self.assertIn("in:sent to:personal@example.com", query)
        self.assertIn(result.document_hash, query)

    def test_po_delivery_accepts_id_only_send_response(self):
        flow = ProcurementFlow()

        def execute(action_name, **kwargs):
            if action_name == gmail_tools.GMAIL_FETCH_EMAILS:
                return {"messages": []}
            return {"id": "sent-po"}

        with tempfile.TemporaryDirectory(prefix="procurement-po-") as temp_dir, patch.object(
            flow_main, "run_composio_action", side_effect=execute
        ):
            result = flow._dispatch_purchase_order(
                self._po_document(), self._po_rfq(), Mock(), Path(temp_dir)
            )
        self.assertEqual((result.status, result.gmail_message_id), ("sent", "sent-po"))
        self.assertFalse(result.reused)
        self.assertEqual(result.attempts, 1)

    def test_po_ambiguous_success_polls_sent_without_resending(self):
        flow = ProcurementFlow()
        calls = []

        def execute(action_name, **kwargs):
            calls.append(action_name)
            return {"messages": []} if action_name == gmail_tools.GMAIL_FETCH_EMAILS else {}

        with tempfile.TemporaryDirectory(prefix="procurement-po-") as temp_dir, patch.object(
            flow_main, "run_composio_action", side_effect=execute
        ), patch.object(flow_main.time, "sleep"):
            result = flow._dispatch_purchase_order(
                self._po_document(), self._po_rfq(), Mock(), Path(temp_dir)
            )
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.attempts, 1)
        self.assertEqual(calls.count(gmail_tools.GMAIL_SEND_EMAIL), 1)
        self.assertIn("verifiable message ID", result.error)

    def test_po_definitive_failures_retry_three_times(self):
        flow = ProcurementFlow()
        sends = 0

        def execute(action_name, **kwargs):
            nonlocal sends
            if action_name == gmail_tools.GMAIL_FETCH_EMAILS:
                return {"messages": []}
            sends += 1
            raise RuntimeError("mailbox unavailable")

        with tempfile.TemporaryDirectory(prefix="procurement-po-") as temp_dir, patch.object(
            flow_main, "run_composio_action", side_effect=execute
        ), patch.object(flow_main.time, "sleep"):
            result = flow._dispatch_purchase_order(
                self._po_document(), self._po_rfq(), Mock(), Path(temp_dir)
            )
        self.assertEqual((result.status, result.attempts), ("failed", 3))
        self.assertEqual(sends, 3)
        self.assertIn("mailbox unavailable", result.error)


if __name__ == "__main__":
    unittest.main()
