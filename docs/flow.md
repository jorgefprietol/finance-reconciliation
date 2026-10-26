# Flujo de operación

![Flujo de operación](diagrams/flow.svg)

[Abrir SVG](diagrams/flow.svg) · [Fuente Mermaid](diagrams/flow.mmd)


<details>
<summary>Versión Mermaid</summary>

```mermaid
flowchart TD
    Start["Recibir lote de banco y libro"] --> Validate["Validar importes, monedas y fechas"]
    Validate --> Existing{"¿Lote ya registrado?"}
    Existing -->|Sí| Fingerprint{"¿Mismo origen normalizado?"}
    Fingerprint -->|Sí| Previous["Devolver resultado conservado"]
    Fingerprint -->|No| Reject["Rechazar conflicto de lote"]
    Existing -->|No| Match["Comparar referencia, importe, moneda y fecha"]
    Match --> Unique{"¿Candidato único en ambos lados?"}
    Unique -->|Sí| Pair["Registrar par conciliado"]
    Unique -->|No| Exception["Conservar excepción"]
    Exception --> Review["Revisar con actor y motivo"]
    Pair --> Metrics["Calcular diferencias y métricas por moneda"]
    Review --> Metrics
    Metrics --> Save["Guardar resultado y auditoría"]
```

</details>

- La conciliación automática no depende del orden de entrada y no convierte divisas.
- La revisión puede vincular movimientos pendientes, sin alterar importes ni monedas ni reutilizar un movimiento.
- `explain` recibe métricas agregadas; el texto opcional no autoriza pagos ni reemplaza el resultado estructurado.

Las operaciones del dominio se guardan junto a auditoría y respuesta idempotente en la transacción del servicio local. Un error revierte los cambios de esa solicitud.

[Arquitectura](architecture.md) · [Tecnologías y alcance](technologies.md)
