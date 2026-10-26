# Tecnologías y alcance

Python 3.10+, Decimal, importes enteros y SQLite. El resumen de resultados puede utilizar Ollama; se incluyen workflow n8n y archivos Docker.

| Tecnología | Estado | Uso en este proyecto |
| --- | --- | --- |
| Python 3.10+ / Decimal / datetime | Implementado | Validación de texto decimal y fechas; contrato monetario de dos decimales. |
| Importes enteros y relación de candidatos | Implementado | Emparejamiento uno a uno sin redondeo por coma flotante. |
| SQLite / SHA-256 | Implementado | Lotes persistentes, huella del origen, revisión y auditoría. |
| API HTTP / consola / CLI | Implementado | Operaciones reconcile, status, resolve y explain autenticadas. |
| Ollama | Opcional | Explica métricas agregadas; requiere modelo configurado y evaluación de su texto. |
| n8n / Docker Compose | Archivos incluidos | Workflow de entrada y empaquetado; runtime y credenciales pendientes de validar. |
| unittest / GitHub Actions | Implementado | Regresiones monetarias, ambigüedad, revisión, transacciones y HTTP. |
| Banco y ERP | Por conectar | La implementación no modifica saldos, crea asientos ni ejecuta pagos. |

“Implementado” describe código disponible y comprobable en el repositorio. “Opcional” requiere un proveedor configurado; “incluido” identifica un archivo o adaptador entregado, sin afirmar una integración externa ejecutada.

[Arquitectura](architecture.md) · [Flujo de operación](flow.md) · [Integraciones](integrations.md)
