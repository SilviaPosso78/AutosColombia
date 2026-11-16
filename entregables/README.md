# Actividad 2 — Autos Colombia

La versión de entrega es `Autos_Colombia_Actividad_2_Final.docx`. Incluye requisitos funcionales y no funcionales, casos de uso, historias de usuario, mockups, secuencias y componentes de las iteraciones 1 y 2, y trazabilidad con el plan de pruebas.

Los modelos editables están en `Fuentes_Actividad_2/Autos_Colombia_Actividad_2.mdj`. Los siete mockups SVG de esa carpeta pueden importarse a Figma. La estructura y referencias del MDJ se comprobaron; su apertura en StarUML quedó pendiente de verificar.

## Revisión general del proyecto — 15 de noviembre de 2026

- Compilación de producción de Angular completada.
- Dependencias Python consistentes (`pip check`), conexión PostgreSQL mediante `SELECT 1` y revisión Alembic `0006 (head)`, sin aplicar migraciones.
- Recorrido HTTP de la aplicación con PostgreSQL: login real de ambos roles, rechazo de credenciales incorrectas, permisos, cookie HttpOnly, cambio de contraseña, revocación al cerrar sesión y vencimiento de sesión.
- Recorrido HTTP transaccional de negocio: catálogo de 80 celdas, creación, edición y eliminación de celda, duplicados, clientes y vehículos; tarifas de moto y camioneta, idempotencia del pago, compatibilidad de espacios, ingreso y tiquete persistido; bloqueo de salida por mensualidad vencida, renovación, salida, liberación del espacio e historial de movimientos.
- Comprobados los dos avisos de cada pago: cinco días antes y el día del vencimiento. WhatsApp está deshabilitado y requiere configurar la integración con Meta.

Las cuentas temporales de revisión se eliminaron y los registros de negocio del recorrido se revirtieron. No se añadieron suites ni herramientas de tests al repositorio.

Esta revisión comprueba compilación y comportamiento HTTP; no equivale a una revisión visual completa del navegador ni sustituye las evidencias individuales de los 30 casos del Excel.

## Ejecución individual del plan

El [Excel diligenciado y sus evidencias](../outputs/validacion_20261115/README.md) registran la reejecución de los 30 casos contra la API y PostgreSQL. Las 30 comprobaciones de API aprobaron; el estado integral es 22 aprobados y 8 bloqueados por variantes visuales sin completar. El control de Chrome se detuvo automáticamente por no poder determinar la URL con suficiente confianza. El plan conserva estos pendientes y no se declara cerrado.
