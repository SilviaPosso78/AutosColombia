# Ejecución del plan de pruebas

Fecha: 2026-11-15, America/Bogota. Versión probada: f7f7164528bc069972637230a46faacad0a43cba.

Se ejecutaron las comprobaciones HTTP y de persistencia de los **30 casos**: todas aprobaron su parte de API. Se verificó parcialmente la interfaz de Chrome. El estado integral es **22 aprobados y 8 bloqueados**, sin fallos funcionales demostrados en esta ejecución.

Los bloqueados son US-04, US-05, US-07, US-10, CE-02, CE-03, CE-06, CE-10. Sus variantes visuales pendientes se detallan en cada evidencia y en el Excel. INC-UI-01: el control de navegador terminó automáticamente al no poder determinar su URL con suficiente confianza; no se continuó operando la aplicación. El plan no se declara cerrado.

La API se ejecutó mediante el transporte ASGI de HTTPX contra FastAPI y PostgreSQL real, sin reemplazar las dependencias de autorización. Para los casos de celdas, la sesión de negocio se vinculó a transacciones aisladas con rollback; la comprobación de catálogo vacío tampoco fue visible fuera de su transacción. La concurrencia ejecutó dos solicitudes a la vez con conexiones independientes. No se creó una base separada ni se aplicaron migraciones.

Se usaron cuentas y códigos ficticios equivalentes a los de la plantilla, con sufijos únicos para evitar interferencia. Los datos transaccionales se revirtieron; los datos temporales confirmados se limpiaron. Se verificaron 80 celdas y cero cuentas temporales restantes. El historial operativo existente se conservó.

Cada archivo de evidencias identifica el caso, la fecha, el responsable técnico, el resultado observado y los estados HTTP esperados/recibidos. No contiene credenciales, hashes ni cookies. No se atribuye la ejecución a los estudiantes ni se completa el dictamen del docente.

El Excel conserva las dos hojas, los requisitos A:G de los 30 casos, las fórmulas de seguimiento y las fórmulas de integridad N. Las filas se ajustaron para leer los resultados. Los estados anteriores sin evidencia completa se sustituyeron por esta reejecución fechada.
