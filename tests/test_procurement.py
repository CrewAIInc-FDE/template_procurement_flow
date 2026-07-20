import json
import os
import unittest
from unittest.mock import patch

from procurement_flow.main import ProcurementFlow
from procurement_flow.procurement import (
    build_quote_review,
    generate_purchase_orders,
    materialize_awards,
    parse_award_feedback,
    validate_awards,
)
from procurement_flow.tools.custom_tool import extract_pdf_text


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
            os.environ.pop("CREWAI_PLATFORM_INTEGRATION_TOKEN", None)
            flow.run_quote_collection()
        flow.finish_no_quotes()
        self.assertEqual(flow.state.final_status, "awaiting_quotes")
        self.assertIn("Gmail is not configured", flow.state.warnings[0])


if __name__ == "__main__":
    unittest.main()
