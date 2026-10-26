"""One-to-one reconciliation in integer minor units; ambiguity stays unresolved."""
import hashlib
import json
import os
import re
from datetime import date
from decimal import Decimal, InvalidOperation

TITLE = "Finance Reconciliation"
DESCRIPTION = "Conciliación bancaria reproducible, coincidencias únicas y excepciones auditables."
SUPPORTED_CURRENCIES = {"USD", "EUR", "GBP", "CAD", "AUD", "CHF", "MXN", "BRL", "COP", "PEN", "ARS"}
DEMO = {"action": "reconcile", "batch_id": "DEMO-2026-10", "date_tolerance_days": 2, "bank": [{"id": "B-1", "date": "2026-10-24", "amount": "143.75", "currency": "USD", "reference": "PAY-042"}, {"id": "B-2", "date": "2026-10-25", "amount": "80.00", "currency": "USD", "reference": "PAY-043"}], "ledger": [{"id": "L-1", "date": "2026-10-25", "amount": "143.75", "currency": "USD", "reference": "pay 042"}, {"id": "L-2", "date": "2026-10-25", "amount": "79.00", "currency": "USD", "reference": "PAY-043"}]}


def _schema(store):
    store.connection.execute("CREATE TABLE IF NOT EXISTS reconciliations (batch_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, source TEXT NOT NULL, result TEXT NOT NULL)")


def _entries(values, label):
    if not isinstance(values, list) or len(values) > 1000:
        raise ValueError(label + " debe ser una lista de máximo 1000 movimientos")
    result, seen = [], set()
    for entry in values:
        if not isinstance(entry, dict):
            raise ValueError("Movimiento inválido")
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not re.fullmatch(r"[A-Za-z0-9._/-]{1,80}", entry_id) or entry_id in seen:
            raise ValueError("Identificador inválido o duplicado en " + label)
        seen.add(entry_id)
        amount = entry.get("amount")
        if not isinstance(amount, str) or not re.fullmatch(r"-?\d+(?:\.\d{1,2})?", amount):
            raise ValueError("amount debe ser texto decimal con máximo dos decimales")
        try:
            minor = int(Decimal(amount) * 100)
        except (InvalidOperation, ValueError, OverflowError):
            raise ValueError("Importe inválido") from None
        if minor == 0 or abs(minor) > 99_999_999_999:
            raise ValueError("Importe cero o fuera de rango")
        currency = entry.get("currency")
        if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError("currency debe ser un código de tres letras")
        if currency not in SUPPORTED_CURRENCIES:
            raise ValueError("Moneda fuera del contrato de dos decimales admitido")
        try:
            if not isinstance(entry.get("date"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["date"]):
                raise ValueError("Formato de fecha inválido")
            day = date.fromisoformat(entry.get("date"))
        except (ValueError, TypeError):
            raise ValueError("Fecha inválida") from None
        reference = entry.get("reference", "")
        if not isinstance(reference, str) or len(reference) > 120:
            raise ValueError("Referencia inválida")
        result.append({"id": entry_id, "date": day.isoformat(), "minor": minor, "currency": currency, "reference": re.sub(r"[^A-Z0-9]", "", reference.upper())})
    return result


def _calculate(bank, ledger, tolerance):
    candidates = {b["id"]: [l["id"] for l in ledger if b["reference"] and l["reference"] == b["reference"] and b["minor"] == l["minor"] and b["currency"] == l["currency"] and abs((date.fromisoformat(b["date"]) - date.fromisoformat(l["date"])).days) <= tolerance] for b in bank}
    reverse = {l["id"]: [bid for bid, lids in candidates.items() if l["id"] in lids] for l in ledger}
    matches = [{"bank_id": bid, "ledger_id": lids[0], "method": "reference_amount_currency_date"} for bid, lids in candidates.items() if len(lids) == 1 and len(reverse[lids[0]]) == 1]
    bank_matched = {m["bank_id"] for m in matches}
    ledger_matched = {m["ledger_id"] for m in matches}
    exceptions = []
    for side, entries, matched, mapping in (("bank", bank, bank_matched, candidates), ("ledger", ledger, ledger_matched, reverse)):
        for entry in entries:
            if entry["id"] not in matched:
                reason = "missing_reference" if not entry["reference"] else "ambiguous" if mapping[entry["id"]] else "no_match"
                exceptions.append({"side": side, "entry_id": entry["id"], "reason": reason, "candidate_ids": mapping[entry["id"]]})
    currencies = sorted({e["currency"] for e in bank + ledger})
    balances = {currency: sum(e["minor"] for e in bank if e["currency"] == currency) - sum(e["minor"] for e in ledger if e["currency"] == currency) for currency in currencies}
    return {"matches": matches, "exceptions": exceptions, "balance_difference_minor": balances, "metrics": {"bank_entries": len(bank), "ledger_entries": len(ledger), "matched_pairs": len(matches), "exception_entries": len(exceptions), "bank_match_rate": len(matches) / len(bank) if bank else None}, "state": "balanced" if not exceptions and all(v == 0 for v in balances.values()) else "requires_review"}


def process(payload, store):
    _schema(store)
    action = payload.get("action", "reconcile")
    batch_id = payload.get("batch_id")
    if not isinstance(batch_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]{3,80}", batch_id):
        raise ValueError("batch_id requerido, entre 3 y 80 caracteres")
    if action == "reconcile":
        tolerance = payload.get("date_tolerance_days", 2)
        if isinstance(tolerance, bool) or not isinstance(tolerance, int) or not 0 <= tolerance <= 7:
            raise ValueError("date_tolerance_days debe estar entre 0 y 7")
        bank, ledger = _entries(payload.get("bank"), "bank"), _entries(payload.get("ledger"), "ledger")
        source = {"bank": bank, "ledger": ledger, "date_tolerance_days": tolerance}
        fingerprint = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
        previous = store.connection.execute("SELECT * FROM reconciliations WHERE batch_id=?", (batch_id,)).fetchone()
        if previous:
            if previous["fingerprint"] != fingerprint:
                raise ValueError("El lote ya existe con otros movimientos")
            return dict(json.loads(previous["result"]), duplicate=True)
        result = dict(_calculate(bank, ledger, tolerance), batch_id=batch_id, duplicate=False)
        store.connection.execute("INSERT INTO reconciliations VALUES (?,?,?,?)", (batch_id, fingerprint, json.dumps(source), json.dumps(result)))
        store.event("reconciliation_completed", {"batch_id": batch_id, "matched_pairs": len(result["matches"]), "exception_entries": len(result["exceptions"])})
        return result
    row = store.connection.execute("SELECT * FROM reconciliations WHERE batch_id=?", (batch_id,)).fetchone()
    if not row:
        raise ValueError("Lote inexistente")
    result = json.loads(row["result"])
    if action == "status":
        return result
    if action == "explain":
        summary = {"metrics": result["metrics"], "balance_difference_minor": result["balance_difference_minor"], "exception_reasons": [e["reason"] for e in result["exceptions"]]}
        backend = os.environ.get("MODEL_BACKEND", "local")
        text = f"{result['metrics']['matched_pairs']} pares conciliados; {len(result['exceptions'])} movimientos requieren revisión. Diferencias en unidades mínimas: {result['balance_difference_minor']}."
        if backend != "local":
            from .providers import generate
            text = generate(json.dumps(summary), system="Explica únicamente las métricas de conciliación recibidas. Los importes están en centavos. No autorices pagos ni inventes causas o cifras.")
        return {"batch_id": batch_id, "explanation": text, "backend": backend, "authoritative_metrics": summary}
    if action == "resolve":
        actor, reason = payload.get("actor"), payload.get("reason")
        if not isinstance(actor, str) or not actor.strip() or not isinstance(reason, str) or len(reason.strip()) < 8:
            raise ValueError("actor y motivo de al menos ocho caracteres requeridos")
        bid, lid = payload.get("bank_id"), payload.get("ledger_id")
        if any(m["bank_id"] == bid or m["ledger_id"] == lid for m in result["matches"]):
            raise ValueError("Movimiento ya conciliado")
        source = json.loads(row["source"])
        bank = next((e for e in source["bank"] if e["id"] == bid), None)
        ledger = next((e for e in source["ledger"] if e["id"] == lid), None)
        if bank is None or ledger is None:
            raise ValueError("Movimiento inexistente")
        if bank["minor"] != ledger["minor"] or bank["currency"] != ledger["currency"]:
            raise ValueError("La revisión manual no puede alterar importes ni monedas")
        result["matches"].append({"bank_id": bid, "ledger_id": lid, "method": "manual_review", "actor": actor[:80], "reason": reason[:300]})
        result["exceptions"] = [e for e in result["exceptions"] if not ((e["side"] == "bank" and e["entry_id"] == bid) or (e["side"] == "ledger" and e["entry_id"] == lid))]
        used_bank = {m["bank_id"] for m in result["matches"]}
        used_ledger = {m["ledger_id"] for m in result["matches"]}
        for exception in result["exceptions"]:
            used = used_ledger if exception["side"] == "bank" else used_bank
            exception["candidate_ids"] = [candidate for candidate in exception["candidate_ids"] if candidate not in used]
            if exception["reason"] == "ambiguous" and not exception["candidate_ids"]:
                exception["reason"] = "no_match"
        result["metrics"].update(matched_pairs=len(result["matches"]), exception_entries=len(result["exceptions"]), bank_match_rate=len(result["matches"]) / len(source["bank"]) if source["bank"] else None)
        result["state"] = "balanced" if not result["exceptions"] and all(v == 0 for v in result["balance_difference_minor"].values()) else "requires_review"
        store.connection.execute("UPDATE reconciliations SET result=? WHERE batch_id=?", (json.dumps(result), batch_id))
        store.event("reconciliation_manually_resolved", {"batch_id": batch_id, "bank_id": bid, "ledger_id": lid, "actor": actor[:80]})
        return result
    raise ValueError("Acción desconocida")
