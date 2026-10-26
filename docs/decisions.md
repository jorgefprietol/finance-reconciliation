# Decisiones de diseño

1. **Unidades mínimas enteras.** Los contratos monetarios evitan flotantes y redondeos ocultos. Las monedas con cero o tres decimales necesitan un contrato adicional y no deben cargarse como si tuvieran dos.
2. **Correspondencia uno a uno.** No se implementan agrupaciones de facturas, pagos parciales, comisiones ni conciliación de muchos a muchos. Estos casos permanecen como excepciones hasta modelar reglas específicas.
3. **Ambigüedad conservadora.** Dos candidatos equivalentes no se resuelven por posición, fecha más cercana o decisión de un modelo. El usuario revisa la evidencia y elige un par explícito.
4. **Origen inmutable.** Los ajustes contables se realizan en el sistema responsable y se cargan como un nuevo lote. La revisión local no cambia importes ni monedas.
5. **Revisión trazable.** `actor` y motivo documentan la decisión. Un despliegue multiusuario debe derivar el actor de una identidad verificada y aplicar autorización; el token de servicio no implementa segregación de funciones.
6. **Explicación separada.** El texto opcional describe el resultado; los números devueltos por el motor determinista son la fuente de verdad.
