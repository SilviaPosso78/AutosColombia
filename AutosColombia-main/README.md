# Autos Colombia

Sistema para un parqueadero por mensualidades: Angular 22, FastAPI y PostgreSQL.

## Funcionalidades

- **Inicio:** resumen de ocupación y disponibilidad real.
- **Control de acceso:** registro de entradas y salidas, validación de mensualidad
  y compatibilidad del vehículo con la celda, consulta por placa y tiquete de entrada.
- **Clientes:** registro y actualización de clientes, responsables de uno o varios vehículos.
- **Operadores:** registro y actualización de los empleados del parqueadero.
- **Vehículos:** placa única, tipo y cliente responsable.
- **Celdas:** catálogo administrable con creación, búsqueda, edición y eliminación. Las celdas con estancias relacionadas conservan su historial. El catálogo inicial contiene 80 espacios.
- **Pagos:** mensualidades, renovaciones e historial independiente por vehículo.
- **Movimientos:** consulta bajo demanda por placa, fechas, celda, operador y
  entrada/salida; reimpresión de tiquetes.

Las mensualidades nuevas y renovaciones tienen tarifa fija: **$250.000 COP para
automóviles y camionetas** y **$100.000 COP para motos**. El importe se muestra
automáticamente y el backend rechaza valores diferentes. Los pagos históricos
conservan su valor registrado.

La vigencia incluye el día final: una mensualidad del 20 de octubre al 20 de
noviembre permite operar hasta el 20 inclusive. Desde el 21 se bloquea el ingreso
si no se renueva. Una salida con mensualidad vencida requiere registrar primero
el pago; después se registra la salida y se libera la celda.

Cada entrada genera un tiquete digital e imprimible con número, placa, tipo,
fecha/hora, celda, puerta y operador. Se conservan los datos del ingreso para
reimpresiones e historial, sin incluir datos personales innecesarios.

## Alcance de esta entrega

El alcance se ajusta al plan de pruebas del Excel. Usuario es una cuenta de acceso con rol ADMINISTRADOR u OPERADOR. Un operador tiene su perfil de empleado vinculado. Los clientes conservan su gestión independiente.

El administrador crea cuentas y administra celdas. El operador consulta disponibilidad y registra entradas y salidas. La API rechaza operaciones del otro rol con 403 y solicitudes sin sesión válida con 401. Los movimientos identifican al perfil de la sesión.

Los avisos de WhatsApp están preparados para **5 días antes** y **el día del
vencimiento**. El envío automático permanece deshabilitado hasta configurar
WhatsApp Business Cloud API, una plantilla aprobada y el webhook. La pantalla
informa si falta configuración; abrir un mensaje manual no confirma su envío.
Consulta [la configuración de WhatsApp](backend/README.md#avisos-por-whatsapp-business).

## Activar cuentas y sesiones

La migración `0006_usuarios_sesiones.py` agrega `usuario` y `sesion`. Debe revisarse y autorizarse antes de aplicarla en una base existente. El login requiere esta revisión.

Después de aplicar la migración, desde `backend`, ejecuta una sola vez lo siguiente.

```powershell
.\.venv\Scripts\python.exe iniciar_usuarios.py
```

El comando crea `admin_prueba` y `operador_prueba` con contraseñas aleatorias. Los accesos se guardan únicamente en `backend/tmp/acceso_inicial.txt`, excluido de Git. El script exige que no existan cuentas y evita reemplazar accesos anteriores. Las cuentas posteriores se crean desde Crear usuarios.

Abre `/login`. La cuenta administradora permite Crear usuarios y Gestionar celdas. El operador accede a Control de acceso y a los módulos operativos existentes. Las sesiones duran ocho horas y se revocan en el servidor al cerrar sesión. Un administrador puede revocar las sesiones de una cuenta desde Crear usuarios.

Para cambiar tu contraseña, ingresa y selecciona **Cambiar contraseña** junto a Cerrar sesión. Completa la clave actual, la nueva y su confirmación. Al guardar se revocan las sesiones y debes ingresar con la nueva clave. El archivo de accesos iniciales conserva las contraseñas originales.

Las contraseñas se guardan con scrypt y sal individual. La cookie de sesión es HttpOnly y SameSite Strict, y usa Secure al servir por HTTPS. La base guarda el hash del token de sesión. El frontend restaura la sesión mediante `/auth/me` y redirige a login al recibir 401. La validación del servidor exige campos y roles válidos y omite los datos recibidos en mensajes de error.

El proxy incluye `/auth/**`, `/usuarios` y `/usuarios/**`. Reinicia Angular si estaba abierto antes de este ajuste.

El Excel conserva sus resultados de ejecución. La correspondencia funcional no certifica los estados Aprobado que ya contiene y cada caso debe ejecutarse con sus evidencias.

## Requisitos

- Python 3.13.
- Node.js 24, mínimo 24.15.0, y npm (entorno verificado con npm 11.7.0).
- PostgreSQL y una base local `autos_colombia` con permisos para la aplicación.
- PowerShell para los comandos siguientes.

Ejecuta los comandos desde esta carpeta, que contiene `backend` y `frontend`.

## Instalación

```powershell
py -3.13 -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Push-Location frontend
try { npm.cmd ci } finally { Pop-Location }
```

Copia `backend/.env.example` a `backend/.env` **solo si no existe** y completa las
variables `DB_*` con tu configuración local. Conserva `WHATSAPP_ENABLED=false`
hasta disponer de la integración. No publiques `.env` ni credenciales.

```powershell
if (-not (Test-Path -LiteralPath backend/.env)) {
    Copy-Item -LiteralPath backend/.env.example -Destination backend/.env
}
.\backend\.venv\Scripts\python.exe backend/check_db.py
```

La comprobación ejecuta `SELECT 1`; no crea la base ni modifica tablas.

### Preparar una base nueva

La revisión vigente es **0006**, con historial `0001 → 0002 → 0003 → 0004 → 0005 → 0006`.
Primero revisa el SQL; el segundo bloque sí modifica el esquema y debe ejecutarse
únicamente después de aprobarlo para la base elegida. No es necesario repetirlo
en una base ya actualizada.

```powershell
Push-Location backend
try {
    .\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head --sql
} finally { Pop-Location }
```

```powershell
Push-Location backend
try {
    .\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Falló la migración.' }
    .\.venv\Scripts\python.exe configurar_celdas.py
    if ($LASTEXITCODE -ne 0) { throw 'Falló la configuración de celdas.' }
} finally { Pop-Location }
```

El catálogo se prepara de forma transaccional y puede repetirse. Conserva ids e
historial; los códigos ajenos al catálogo requieren revisar su correspondencia.
Los clientes, operadores, vehículos y pagos se registran desde la aplicación.

## Ejecutar en dos terminales de PowerShell

En la primera terminal, desde esta carpeta:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

En la segunda:

```powershell
Set-Location frontend
npm.cmd start -- --host 127.0.0.1 --port 4200
```

- Aplicación: <http://127.0.0.1:4200>.
- Documentación API: <http://127.0.0.1:8000/docs>.
- Salud: <http://127.0.0.1:8000/health> (`/health` no comprueba PostgreSQL).

Angular usa el proxy de desarrollo hacia `127.0.0.1:8000`. Reinicia Angular si
cambias `frontend/proxy.conf.json`. Una compilación de producción necesita que
el servidor web dirija las rutas de API al backend.

## Comprobaciones manuales

Desde esta carpeta:

```powershell
.\backend\.venv\Scripts\python.exe -m pip check
.\backend\.venv\Scripts\python.exe backend/check_db.py
Push-Location frontend
try {
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la compilacion.' }
} finally { Pop-Location }
```

Esta entrega no incluye tests automatizados. Con los servidores activos, revisa
entradas, salidas, compatibilidad de celdas, pagos, vigencia, historial y tiquetes
desde la aplicación. La API se puede consultar en /docs.

## Archivos del repositorio

Se conservan código, migraciones, documentación, `requirements.txt`,
`package.json`, `package-lock.json` y `.env.example` con marcadores públicos.
Se excluyen credenciales, entornos virtuales, dependencias instaladas, cachés,
compilaciones, registros y datos locales. La base PostgreSQL no se incluye en Git;
se reconstruye con las migraciones y el catálogo explícito.

Más detalles en [backend/README.md](backend/README.md) y
[frontend/README.md](frontend/README.md).
