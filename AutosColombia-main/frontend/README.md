# Frontend de Autos Colombia

Angular 22 con componentes standalone, TypeScript estricto, formularios reactivos
y CSS. Usa las dependencias locales y conserva `package-lock.json`.

## Ejecutar

Desde `frontend`, con el backend activo en el puerto 8000:

```powershell
npm.cmd ci
npm.cmd start -- --host 127.0.0.1 --port 4200
```

Abre <http://127.0.0.1:4200>. La instalación del backend y PostgreSQL se explica
en el [README principal](../README.md#instalación).

## Pantallas

| Pantalla | Ruta | Función |
| --- | --- | --- |
| Inicio | `/` | Resumen de ocupación y disponibilidad real. |
| Control de acceso | `/control-acceso` | Entrada, consulta por placa, salida y tiquete. |
| Movimientos | `/gestion/movimientos` | Reporte con filtros, totales y reimpresión. |
| Pagos | `/gestion/pagos` | Mensualidades, renovaciones, historial y avisos. |
| Vehículos | `/gestion/vehiculos` | Vehículos y su cliente responsable. |
| Clientes | `/gestion/clientes` | Clientes y sus datos de contacto. |
| Celdas | `/gestion/celdas` | Creación, consulta, edición y eliminación por administrador. |
| Operadores | `/gestion/operadores` | Empleados del parqueadero. |
| Tiquete | `/tiquetes/:id` | Documento digital e imprimible de una entrada. |

La administración de celdas corresponde al rol ADMINISTRADOR. El operador consulta disponibilidad en Control de acceso. La compatibilidad se determina por el tipo de celda, incluso si su código cambia.

Pagos muestra automáticamente la tarifa fija: automóviles y camionetas $250.000 COP,
motos $100.000 COP. El backend valida el importe. Cada vehículo tiene su propio
periodo y pago; el UUID de solicitud permite reintentar sin duplicar un pago.

Los avisos se programan cinco días antes y el día del vencimiento. La pantalla
informa si WhatsApp está pendiente de configuración. **Abrir WhatsApp** prepara
un mensaje manual; no confirma su envío. Consulta la
[configuración del backend](../backend/README.md#avisos-por-whatsapp-business).

El tiquete conserva los datos originales del ingreso y dispone de estilos de
impresión. Los documentos históricos reconstruidos se identifican como tales.

El login está en `/login`. El administrador accede a Crear usuarios y Gestionar celdas. El operador accede a los módulos operativos. Las rutas y menús aplican el rol, y la API valida cada solicitud. La sesión se restaura mediante `/auth/me` y se revoca mediante `/auth/logout`.

## Conexión con la API

Los servicios usan rutas relativas y `API_BASE_URL`. El proxy de desarrollo
`proxy.conf.json` dirige salud, clientes, operadores, vehículos, celdas, estancias,
auth, usuarios, pagos, mensualidades y notificaciones a `127.0.0.1:8000`. Reinicia Angular después
de cambiar ese archivo. El backend requiere las migraciones hasta **0006** y el
catálogo de celdas preparado.

En producción, el servidor web debe dirigir las rutas de API al backend;
`ng build` no incluye un proxy. No coloques secretos en el frontend.

## Verificar

```powershell
npm.cmd run build
```

La salida se guarda en `dist/frontend`. Esta entrega no incluye tests
automatizados. Comprueba los flujos manualmente con el backend y PostgreSQL
activos. Los generadores Angular tienen `skipTests` habilitado.
