import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

TEST_ROOT = tempfile.mkdtemp(prefix="procurement-portal-tests-")
os.environ["DB_PATH"] = os.path.join(TEST_ROOT, "portal.db")
os.environ["DEPLOYMENT_URL"] = ""
sys.path[:0] = ["frontend", "src"]

import app as portal  # noqa: E402


class PortalWorkflowTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_ROOT, ignore_errors=True)

    def setUp(self):
        with portal.db() as conn:
            for table in (
                "purchase_order_items", "purchase_orders", "pending_reviews",
                "kickoffs", "request_artifacts", "request_items", "purchase_requests",
            ):
                conn.execute(f"DELETE FROM {table}")
        portal.set_setting("clp_per_usd", 950)
        self.client = portal.app.test_client()

    def _request(self, item_count=2):
        pr = portal.allocate_pr("E-001", "Need equipment")
        with portal.db() as conn:
            conn.execute(
                "UPDATE purchase_requests SET status='awaiting_quotes', justification='Need equipment'"
                " WHERE pr_number=?", (pr,),
            )
            for index in range(item_count):
                conn.execute(
                    "INSERT INTO request_items"
                    " (pr_number, catalog_item_id, sku, name, quantity, unit_price_usd, line_total_usd)"
                    " VALUES (?,?,?,?,1,100,100)",
                    (pr, f"IT-{index + 1:03d}", f"SKU-{index + 1}", f"Item {index + 1}"),
                )
        return pr

    def _kickoff(self, pr, kickoff_id, mode="quote_review"):
        with portal.db() as conn:
            conn.execute(
                "INSERT INTO kickoffs (kickoff_id, pr_number, mode, state, created_at, updated_at)"
                " VALUES (?,?,?,'pending',?,?)",
                (kickoff_id, pr, mode, portal.now(), portal.now()),
            )

    def _po(self, pr, item_ids, supplier_id="S-1", po_number="PO-1001-01"):
        items = []
        with portal.db() as conn:
            rows = conn.execute(
                f"SELECT * FROM request_items WHERE id IN ({','.join('?' for _ in item_ids)})",
                item_ids,
            ).fetchall()
        for row in rows:
            items.append({
                "request_item_id": row["id"], "catalog_item_id": row["catalog_item_id"],
                "sku": row["sku"], "item_name": row["name"], "quantity": row["quantity"],
                "quote_id": f"Q-{row['id']}", "supplier_id": supplier_id,
                "supplier_name": "Alpha", "unit_price": 100, "currency": "USD",
                "line_total": 100, "line_total_usd": 100, "delivery_days": 2,
                "risk_notes": [],
            })
        return {
            "po_number": po_number, "pr_number": pr, "supplier_id": supplier_id,
            "supplier_name": "Alpha", "total_usd": 100 * len(items),
            "item_ids": item_ids, "items": items, "markdown": f"# {po_number}",
        }

    def test_markdown_fences_are_stripped_without_regex(self):
        self.assertEqual(portal.strip_md_fence("```markdown\n# PO\n```"), "# PO")
        other = "```python\nprint('keep the fence')\n```"
        self.assertEqual(portal.strip_md_fence(other), other)

    def test_intake_stops_at_awaiting_quotes(self):
        pr = portal.allocate_pr("E-001", "Need one laptop")
        self._kickoff(pr, "intake-1", "intake")
        portal.process_envelope(pr, "intake-1", {
            "final_status": "awaiting_quotes",
            "request_draft": {
                "line_items": [{"catalog_item_id": "IT-001", "sku": "LAP", "name": "Laptop",
                                "quantity": 1, "unit_price_usd": 100, "line_total_usd": 100}],
                "justification": "Need one laptop", "urgency": "normal", "unmatched": [],
                "estimated_total_usd": 100, "detected_language": "en",
            },
        })
        with portal.db() as conn:
            status = conn.execute(
                "SELECT status FROM purchase_requests WHERE pr_number=?", (pr,)
            ).fetchone()[0]
            modes = [row[0] for row in conn.execute(
                "SELECT mode FROM kickoffs WHERE pr_number=?", (pr,)
            ).fetchall()]
        self.assertEqual(status, "awaiting_quotes")
        self.assertEqual(modes, ["intake"])

    def test_review_endpoint_is_idempotent(self):
        pr = self._request(1)

        def fake_start(pr_number, mode, inputs):
            self._kickoff(pr_number, "review-1", mode)
            return "review-1"

        with patch.object(portal.amp, "start_kickoff", side_effect=fake_start) as start:
            first = self.client.post(f"/api/requests/{pr}/review-quotes")
            second = self.client.post(f"/api/requests/{pr}/review-quotes")
        self.assertEqual(first.status_code, 202)
        self.assertFalse(first.get_json()["already_running"])
        self.assertTrue(second.get_json()["already_running"])
        self.assertEqual(start.call_count, 1)

    def test_review_endpoint_hides_internal_exception(self):
        pr = self._request(1)
        with patch.object(portal.amp, "start_kickoff", side_effect=RuntimeError("secret-token")):
            response = self.client.post(f"/api/requests/{pr}/review-quotes")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json(), {"error": "could not start quote review"})

    def test_decision_endpoint_hides_internal_exception(self):
        pr = self._request(1)
        with portal.db() as conn:
            conn.execute(
                "INSERT INTO pending_reviews (pr_number, callback_url, memo, received_at)"
                " VALUES (?,?,?,?)", (pr, "https://example.invalid", "{}", portal.now()),
            )
        with patch.object(
            portal.http, "post", side_effect=portal.http.RequestException("secret-token")
        ):
            response = self.client.post(f"/api/requests/{pr}/reject")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json(), {"error": "could not deliver decision"})

    def test_no_quotes_returns_to_awaiting_with_warning(self):
        pr = self._request(1)
        self._kickoff(pr, "review-1")
        portal.process_envelope(pr, "review-1", {
            "final_status": "awaiting_quotes", "warnings": ["Gmail unavailable"],
            "alerts": [{"severity": "medium", "message": "Gmail unavailable"}],
        })
        detail = self.client.get(f"/api/requests/{pr}").get_json()
        self.assertEqual(detail["status"], "awaiting_quotes")
        self.assertEqual(detail["warnings"], ["Gmail unavailable"])

    def test_partial_then_final_award_reuses_one_po(self):
        pr = self._request(2)
        with portal.db() as conn:
            ids = [row[0] for row in conn.execute(
                "SELECT id FROM request_items WHERE pr_number=? ORDER BY id", (pr,)
            ).fetchall()]
        self._kickoff(pr, "review-1")
        portal.process_envelope(pr, "review-1", {
            "final_status": "awaiting_quotes", "purchase_orders": [self._po(pr, [ids[0]])],
        })
        detail = self.client.get(f"/api/requests/{pr}").get_json()
        self.assertEqual(detail["status"], "awaiting_quotes")
        self.assertEqual(len(detail["outstanding_items"]), 1)
        self.assertEqual(len(detail["purchase_orders"]), 1)

        self._kickoff(pr, "review-2")
        portal.process_envelope(pr, "review-2", {
            "final_status": "approved", "purchase_orders": [self._po(pr, ids)],
        })
        detail = self.client.get(f"/api/requests/{pr}").get_json()
        self.assertEqual(detail["status"], "approved")
        self.assertEqual(len(detail["purchase_orders"]), 1)
        self.assertEqual(len(detail["outstanding_items"]), 0)

    def test_portal_approval_sends_exact_structured_selection(self):
        pr = self._request(1)
        with portal.db() as conn:
            item_id = conn.execute(
                "SELECT id FROM request_items WHERE pr_number=?", (pr,)
            ).fetchone()[0]
            proposal = {
                "pr_number": pr, "clp_per_usd": 950, "uncovered_item_ids": [], "warnings": [],
                "lines": [{"request_item_id": item_id, "catalog_item_id": "IT-001", "sku": "SKU",
                           "item_name": "Item", "quantity": 1, "suggested_quote_id": "Q-1",
                           "options": [{"quote_id": "Q-1"}, {"quote_id": "Q-2"}]}],
            }
            conn.execute(
                "INSERT INTO pending_reviews (pr_number, callback_url, memo, received_at)"
                " VALUES (?,?,?,?)", (pr, portal.FIXTURE_CALLBACK, json.dumps(proposal), portal.now()),
            )
            conn.execute(
                "UPDATE purchase_requests SET status='awaiting_review' WHERE pr_number=?", (pr,)
            )
        invalid = self.client.post(
            f"/api/requests/{pr}/approve",
            json={"awards": [{"request_item_id": item_id, "quote_id": "secret-token"}]},
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.get_json(), {"error": "invalid award selection"})
        response = self.client.post(
            f"/api/requests/{pr}/approve",
            json={"awards": [{"request_item_id": item_id, "quote_id": "Q-2"}]},
        )
        self.assertEqual(response.status_code, 200)
        feedback = json.loads(response.get_json()["feedback"])
        self.assertEqual(feedback, {
            "decision": "approved",
            "awards": [{"request_item_id": item_id, "quote_id": "Q-2"}],
        })


if __name__ == "__main__":
    unittest.main()
