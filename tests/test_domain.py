import copy
import tempfile
import unittest
from unittest.mock import patch
from app.domain import DEMO, process
from app.runtime import Store


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name + "/test.db")
        self.payload = copy.deepcopy(DEMO)

    def tearDown(self):
        self.store.connection.close()
        self.temp.cleanup()

    def reconcile(self):
        return process(self.payload, self.store)

    def test_unique_reference_amount_currency_and_date_match(self):
        result = self.reconcile()
        self.assertEqual(result["matches"], [{"bank_id": "B-1", "ledger_id": "L-1", "method": "reference_amount_currency_date"}])
        self.assertEqual(result["balance_difference_minor"], {"USD": 100})

    def test_ambiguity_is_never_resolved_by_order(self):
        self.payload["ledger"].append(dict(self.payload["ledger"][0], id="L-3"))
        result = self.reconcile()
        self.assertEqual(result["matches"], [])
        self.assertEqual(next(e for e in result["exceptions"] if e["entry_id"] == "B-1")["reason"], "ambiguous")

    def test_two_bank_entries_cannot_claim_one_ledger_entry(self):
        self.payload["bank"].append(dict(self.payload["bank"][0], id="B-3"))
        self.assertEqual(self.reconcile()["matches"], [])

    def test_cross_currency_does_not_match(self):
        self.payload["ledger"][0]["currency"] = "EUR"
        result = self.reconcile()
        self.assertEqual(result["matches"], [])
        self.assertEqual(set(result["balance_difference_minor"]), {"USD", "EUR"})

    def test_subcent_precision_is_rejected(self):
        self.payload["bank"][0]["amount"] = "143.751"
        with self.assertRaises(ValueError):
            self.reconcile()

    def test_float_input_is_rejected(self):
        self.payload["bank"][0]["amount"] = 143.75
        with self.assertRaises(ValueError):
            self.reconcile()

    def test_date_outside_tolerance_stays_unmatched(self):
        self.payload["ledger"][0]["date"] = "2026-10-01"
        self.assertEqual(self.reconcile()["matches"], [])

    def test_duplicate_entry_ids_rejected(self):
        self.payload["bank"].append(dict(self.payload["bank"][0]))
        with self.assertRaises(ValueError):
            self.reconcile()

    def test_same_batch_is_replayable_but_not_overwritable(self):
        self.reconcile()
        self.assertTrue(self.reconcile()["duplicate"])
        self.payload["bank"][0]["amount"] = "1.00"
        with self.assertRaises(ValueError):
            self.reconcile()

    def test_missing_reference_requires_review(self):
        self.payload["bank"][0]["reference"] = ""
        result = self.reconcile()
        self.assertEqual(next(e for e in result["exceptions"] if e["entry_id"] == "B-1")["reason"], "missing_reference")

    def test_manual_resolution_requires_same_currency_and_amount(self):
        self.reconcile()
        with self.assertRaises(ValueError):
            process({"action": "resolve", "batch_id": self.payload["batch_id"], "bank_id": "B-2", "ledger_id": "L-2", "actor": "fin-01", "reason": "Importes distintos"}, self.store)

    def test_manual_resolution_cannot_reuse_movement(self):
        self.payload["ledger"].append(dict(self.payload["ledger"][0], id="L-3"))
        self.reconcile()
        resolution = {"action": "resolve", "batch_id": self.payload["batch_id"], "bank_id": "B-1", "ledger_id": "L-1", "actor": "fin-01", "reason": "Verificado con soporte bancario"}
        result = process(resolution, self.store)
        self.assertEqual(result["metrics"]["matched_pairs"], 1)
        with self.assertRaises(ValueError):
            process(dict(resolution, ledger_id="L-3"), self.store)

    def test_empty_batch_has_no_invented_match_rate(self):
        self.payload.update(bank=[], ledger=[])
        result = self.reconcile()
        self.assertIsNone(result["metrics"]["bank_match_rate"])

    def test_negative_amounts_match_without_losing_sign(self):
        self.payload["bank"][0]["amount"] = "-143.75"
        self.payload["ledger"][0]["amount"] = "-143.75"
        self.assertEqual(len(self.reconcile()["matches"]), 1)

    def test_currency_with_different_minor_unit_contract_rejected(self):
        self.payload["bank"][0]["currency"] = "JPY"
        with self.assertRaises(ValueError):
            self.reconcile()

    def test_model_explanation_receives_aggregates_and_cannot_mutate_result(self):
        self.reconcile()
        with patch.dict("os.environ", {"MODEL_BACKEND": "ollama"}), patch("app.providers.generate", return_value="Resumen redactado") as generate:
            result = process({"action": "explain", "batch_id": self.payload["batch_id"]}, self.store)
        self.assertNotIn("PAY-042", generate.call_args.args[0])
        self.assertEqual(result["authoritative_metrics"]["balance_difference_minor"], {"USD": 100})
        self.assertEqual(process({"action": "status", "batch_id": self.payload["batch_id"]}, self.store)["metrics"]["matched_pairs"], 1)


if __name__ == "__main__":
    unittest.main()
