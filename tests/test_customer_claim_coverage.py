import unittest

from tests.support import IsolatedPipelineTestCase


class CustomerClaimCoverageTests(IsolatedPipelineTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.run_script(
            "rego_controls.py",
            "customer_claim_coverage.py",
        )
        cls.coverage = {row["contract_id"]: row for row in cls.read_processed("customer_claim_coverage.json")}
        cls.summary = cls.read_processed("customer_claim_summary.json")

    def test_each_customer_contract_receives_claim_status(self) -> None:
        self.assertEqual({"C-001", "C-002", "C-003"}, set(self.coverage))
        for row in self.coverage.values():
            self.assertIn(row["claim_status"], {"Covered", "Review", "Shortfall", "Not supportable"})
            self.assertTrue(row["primary_issue"])

    def test_claim_status_is_contract_scoped(self) -> None:
        self.assertEqual("Not supportable", self.coverage["C-001"]["claim_status"])
        self.assertEqual("Not supportable", self.coverage["C-002"]["claim_status"])
        self.assertEqual("Review", self.coverage["C-003"]["claim_status"])
        self.assertEqual(900, self.summary["uncovered_mwh"])
        self.assertEqual(6412.5, self.summary["estimated_cover_cost_gbp"])

    def test_context_is_not_claim_validity_input(self) -> None:
        notes = {row["methodology_note"] for row in self.coverage.values()}
        self.assertEqual(1, len(notes))
        note = notes.pop()
        self.assertIn("Grid intensity and carbon prices are context layers", note)
        self.assertIn("do not determine claim validity", note)


if __name__ == "__main__":
    unittest.main()
