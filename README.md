# Finance Reconciliation

Motor de conciliación entre movimientos bancarios y contables. Compara referencia, importe, moneda y tolerancia de fecha; solo concilia automáticamente relaciones únicas en ambos lados. Los empates quedan pendientes para revisión.

## Ejecutar

Requiere Python 3.10 o posterior. La demo utiliza un lote sintético con un par conciliado y una diferencia de un dólar.

```powershell
python -m app demo
python -m unittest discover -s tests -v
$env:SERVICE_TOKEN = 'un-token-local-de-al-menos-24-caracteres'
python -m app serve
```

Abra `http://127.0.0.1:8080`. Para la API, envíe `POST /api/run`, `Authorization: Bearer <SERVICE_TOKEN>` e `Idempotency-Key`. Cada solicitud se registra de forma atómica junto a su respuesta.

## Conciliar

```json
{
  "action": "reconcile",
  "batch_id": "BANK-2026-10-26",
  "date_tolerance_days": 2,
  "bank": [{"id":"B-1","date":"2026-10-24","amount":"143.75","currency":"USD","reference":"PAY-042"}],
  "ledger": [{"id":"L-1","date":"2026-10-25","amount":"143.75","currency":"USD","reference":"pay 042"}]
}
```

Los importes se envían como texto decimal y se convierten a unidades mínimas enteras. No se admiten flotantes, ceros ni más de dos decimales. Se preserva el signo de los egresos. El contrato admite USD, EUR, GBP, CAD, AUD, CHF, MXN, BRL, COP, PEN y ARS; otras monedas se rechazan. No realiza conversión de divisas.

Las referencias se normalizan a caracteres alfanuméricos en mayúsculas. Una referencia vacía nunca genera una conciliación automática. La tolerancia es de cero a siete días naturales; cada lado admite hasta mil movimientos por lote.

La salida contiene `matches`, `exceptions`, diferencias por moneda y métricas del lote. `bank_match_rate` divide pares conciliados entre movimientos del banco; es `null` si el banco no contiene movimientos. `balanced` requiere que no queden excepciones y que cada diferencia por moneda sea cero.

## Revisión

`status` recupera un lote. `resolve` vincula un par pendiente con actor y motivo, manteniendo intactos importe y moneda. No es posible reutilizar un movimiento ya conciliado.

```json
{"action":"resolve","batch_id":"BANK-2026-10-26","bank_id":"B-1","ledger_id":"L-1","actor":"finance-01","reason":"Verificado con soporte bancario"}
```

`explain` redacta un resumen de métricas. Puede usar el proveedor de modelo configurado, sin recibir referencias ni autorizar asientos o pagos. Las métricas estructuradas se devuelven junto al texto y conservan su valor original.

## Evidencia y alcance

Las pruebas cubren precisión monetaria, ambigüedad, cardinalidad, moneda, fecha, reenvío de lotes y revisión manual. Un lote existente con otros movimientos produce conflicto, en lugar de sobrescribir el historial. Los datos locales no se envían a bancos ni ERP; la entrada y salida de esos sistemas corresponde a adaptadores externos.

`/api/metrics` mide solicitudes de esta instancia. La tasa de conciliación y las excepciones son observaciones del lote procesado; no equivalen a una reducción comprobada de trabajo. Para medir productividad deben compararse períodos equivalentes con tiempos de revisión y tasas de error reales.

Consulte [arquitectura](docs/architecture.md), [decisiones](docs/decisions.md), [operación](docs/operations.md) y [referencias](docs/references.md).
