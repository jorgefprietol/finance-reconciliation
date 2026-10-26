# Operación

Prepare un identificador estable por extracción. Verifique que cada lado tenga identificadores únicos, importes firmados y moneda correcta. Conserve la extracción original fuera del servicio cuando necesite evidencia contable formal.

Revise primero `missing_reference`, luego `no_match` y finalmente `ambiguous`. Una ausencia de referencia necesita soporte externo; una diferencia de importe o moneda no puede forzarse mediante `resolve`. Registre el ajuste en el sistema de origen antes de cargar un lote nuevo.

La revisión manual puede superar una discrepancia de fecha o referencia cuando existe evidencia, pero mantiene la igualdad de importe y moneda. Después de resolver un par, los candidatos restantes se actualizan sin ejecutar conciliaciones automáticas adicionales. El equipo conserva control explícito sobre el resto del lote.

Para seguimiento use pares conciliados, movimientos pendientes, tasa de conciliación bancaria y diferencia por moneda. No sume monedas distintas. Compare productividad solo con tiempos observados y una definición estable del tamaño de lote y dificultad de las excepciones.

Respalde SQLite con el servicio detenido o mediante backup en línea. Restrinja el acceso a origen y resultados. La huella protege contra sustituciones accidentales dentro del servicio, pero no constituye una firma digital ni sustituye un archivo de auditoría externo.
