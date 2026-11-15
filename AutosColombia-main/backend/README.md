# Backend de Autos Colombia

## Cuentas y autenticación

La revisión 0006 agrega cuentas y sesiones revocables. No cambia los movimientos ni pagos existentes. Ver el README principal para iniciar las cuentas locales y consultar los accesos privados.

| Operación | Permiso y resultado |
| --- | --- |
| POST `/auth/login` | Credenciales válidas devuelven perfil y cookie HttpOnly. Incorrectas devuelven 401 con mensaje genérico. |
| GET `/auth/me` | Devuelve el perfil de una sesión vigente, activa y no revocada. |
| POST `/auth/logout` | Revoca la sesión en PostgreSQL y elimina la cookie. Reutilizarla devuelve 401. |
| POST `/usuarios` | Administrador. Cuenta y perfil operador se crean en una transacción. Duplicados devuelven 409. |
| GET `/usuarios` | Administrador. Listado paginado sin contraseñas ni hashes. |
| POST `/usuarios/{id}/revocar-sesiones` | Administrador. Invalida todas las sesiones de la cuenta. |

Solo existen ADMINISTRADOR y OPERADOR. La creación valida campos obligatorios y rechaza roles arbitrarios con 422. Un administrador no hereda entradas o salidas. El operador recibe 403 al intentar administrar cuentas o celdas. Las rutas operativas existentes quedan disponibles para el operador. El webhook de Meta conserva su verificación de firma.

Las sesiones caducan a las ocho horas. Para comprobar vencimiento en una base aislada se puede adelantar `sesion.vence_en` a un instante anterior al momento de ejecución, manteniéndolo posterior a `creada_en`. Los hashes de contraseña usan scrypt con N 131072, r 8, p 1 y sal de 16 bytes. La comparación es constante y las respuestas de validación omiten el contenido recibido.

## Tiquetes e historial de movimientos

La revisión `0005_tiquetes.py` crea `tiquete`, con una fila por estancia, placa,
tipo, celda, puerta y nombre del operador de entrada guardados. Al cerrar la
estancia se conserva también el nombre del operador de salida de ese momento.
La migración local se aplicó con autorización. El backfill de las estancias
existentes usa sus datos actuales y marca `reconstruido=true`.

```powershell
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade 0004:0005 --sql
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade 0005
```

- `POST /estancias/entrada` conserva los campos anteriores de la respuesta y
  agrega `tiquete`. La estancia y su tiquete se confirman o revierten juntos.
- `GET /estancias/tiquetes/{estancia_id}` devuelve el documento digital con su
  número estable AC- seguido del id de estancia con al menos ocho dígitos.
  La respuesta incluye los datos operativos requeridos y el indicador de
  reconstrucción para documentos anteriores al módulo.
- `GET /estancias/movimientos` consulta entradas y salidas como eventos separados.
  Admite placa, desde, hasta, celda_id, operador_id, movimiento, offset y limit.
  Los días se interpretan de forma inclusiva en America/Bogota. Los resultados
  incluyen tiquete, fecha, puerta y operador de cada evento.
- El reporte usa una sola consulta SQL para la página y los totales de entradas
  y salidas. Conserva totales aunque se solicite una página vacía.

Los movimientos conservan las FK e historial existentes. El tiquete tiene una
clave primaria por estancia que evita generar documentos distintos para el mismo
ingreso. Las restricciones de vigencia y pago se validan antes de ingresar o
cerrar una estancia, y la entrada exige cliente responsable asociado.

Los tiquetes requieren 0005 y el control de acceso requiere además 0006.

## Pagos y mensualidades

Las mensualidades nuevas y renovaciones tienen tarifa fija: automóviles y camionetas $250.000 COP; motos $100.000 COP. El formulario muestra el importe automáticamente y el backend rechaza importes diferentes (HTTP 422). Los pagos históricos conservan su valor registrado.

La revisión `0004_pagos_avisos.py` crea las tablas de pagos y avisos; conserva
las tablas existentes. En la base local se aplicó con autorización del usuario.
Para otra instalación, revisa primero el SQL y aplica la revisión deliberadamente.

```powershell
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade 0003:0004 --sql
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade 0004
```

- `POST /pagos` registra placa, `operador_id`, valor decimal COP, fecha del pago,
  inicio, fin inclusivo y `solicitud_id` UUID. Un mismo UUID con el mismo contenido
  devuelve el pago original; con otro contenido responde 409.
- `GET /pagos` devuelve el historial paginado con filtro opcional por placa.
- `GET /mensualidades` incluye todos los vehículos, cliente y estado calculado
  para la fecha de Bogotá. Admite placa, estado, offset y limit.
- Los estados son SIN_MENSUALIDAD, PROGRAMADA, VIGENTE, POR_VENCER (hasta cinco
  días inclusive) y VENCIDA. Los pagos requieren cliente responsable y operador.
- Una transacción serializa los pagos, valida solapamientos y comprueba la capacidad
  durante todo el periodo, incluidos contratos futuros. Los importes se guardan
  con NUMERIC(12,2). El tipo contratado queda registrado en el pago.
- Entrada y salida requieren un periodo pagado que cubra el día actual. El tipo
  del vehículo se conserva mientras tenga periodos contratados vigentes o futuros.

Los registros de pago se conservan para auditoría con cliente, operador y fecha/hora
real de creación. La aplicación actual selecciona manualmente el operador. El control
de sesión y permisos se aplica mediante las cuentas y sesiones de la revisión 0006. El operador del pago y los movimientos debe coincidir con la sesión.

## Avisos por WhatsApp Business

Cada pago crea dos avisos, cinco días antes y el día del vencimiento. La fecha se
calcula en America/Bogota. El proceso de FastAPI revisa la cola cada 60 segundos,
incluso con el navegador cerrado. Necesita que el backend permanezca ejecutándose.
Con varios procesos, los avisos se reclaman mediante bloqueo y SKIP LOCKED.
Una renovación consecutiva cancela los recordatorios pendientes anteriores.

Para habilitar el canal, completa las variables de `backend/.env` basándote en
`.env.example`. Mantén el token y el secreto fuera del frontend y de Git.

1. Crea o conecta la cuenta de WhatsApp Business Platform en Meta, configura el
   número y obtén su Phone Number ID y token con permiso de mensajería.
2. Solicita una plantilla de utilidad llamada `recordatorio_mensualidad`, idioma
   `es` (o ajusta WHATSAPP_TEMPLATE_NAME y WHATSAPP_TEMPLATE_LANGUAGE). Su cuerpo
   debe usar tres parámetros de texto en este orden, nombre, placa y vencimiento.

   > Hola {{1}}. Autos Colombia te recuerda que la mensualidad del vehículo {{2}} vence el {{3}} inclusive. Puedes renovar tu mensualidad en el parqueadero. Gracias.

3. Configura WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN, WHATSAPP_TEMPLATE_NAME,
   WHATSAPP_APP_SECRET y un WHATSAPP_VERIFY_TOKEN privado. La versión predeterminada
   de la API es v27.0. Usa teléfonos con indicativo internacional; los móviles
   colombianos de diez dígitos iniciados en 3 se normalizan con 57.
4. Publica el backend en una URL HTTPS accesible para Meta y registra
   `/notificaciones/webhook` como callback del campo `messages`. Usa el mismo
   token de verificación y configura el secreto de la app para verificar las
   firmas X-Hub-Signature-256.
5. Confirma que la plantilla esté aprobada y establece WHATSAPP_ENABLED=true.
   Los clientes deben autorizar los recordatorios de WhatsApp del negocio.
   La configuración se vuelve a leer en cada ciclo del proceso.

La cuenta, token y plantilla aprobada se gestionan en Meta. Ver la
[documentación oficial de plantillas de utilidad](https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/utility-templates/utility-templates/).

`GET /notificaciones/configuracion` devuelve disponibilidad y nombres de variables
pendientes. `GET /notificaciones` devuelve la cola paginada. Los estados distinguen
PENDIENTE, EN_PROCESO, ACEPTADO por Meta, ENTREGADO y LEIDO por webhook firmado,
ERROR, REVISION, OMITIDO y CANCELADO. La aceptación de la API conserva su estado
hasta recibir confirmación del proveedor. Las confirmaciones atrasadas conservan
el estado más avanzado y se validan contra el intento de envío.

`POST /notificaciones/{id}/reintentar` admite errores confirmados en la misma fecha
del aviso. Ante un timeout o interrupción, queda en REVISION para comprobar el
resultado en WhatsApp Business antes de repetir. Los avisos de fechas pasadas se
marcan OMITIDO para evitar envíos automáticos fuera de fecha.

## Gestión de clientes

Clientes y operadores son entidades distintas: los clientes son propietarios de
vehículos; los operadores son trabajadores del parqueadero. El CRUD de clientes
está disponible en `/clientes` con creación (201), listado paginado, consulta por
id, actualización parcial y eliminación.

`documento`, `nombre` y `telefono` son obligatorios; el documento se normaliza a
mayúsculas y es único. `correo` es opcional y, si se informa, debe tener formato
de correo. `vehiculo.cliente_id` es opcional: un cliente puede asociarse con
varios vehículos. Al eliminar un cliente, `ON DELETE SET NULL` conserva los
vehículos y elimina solo su asociación.

La migración `0003_clientes.py` se deriva de `0002`. La base local estaba en
`0002 (head)` antes de añadirla y **no se ha actualizado**. No ejecutes una
migración sin decidirlo y respaldar la base. Para revisar el SQL sin conexión ni
cambios persistentes:

```powershell
.\.venv\Scripts\python.exe -m alembic -c .\alembic.ini upgrade 0002:0003 --sql
```

Para aplicarla deliberadamente, desde `backend`:

```powershell
.\.venv\Scripts\python.exe -m alembic -c .\alembic.ini upgrade 0003
.\.venv\Scripts\python.exe -m alembic -c .\alembic.ini current
```

## CRUD de operadores

Disponible únicamente en la API bajo `/operadores`, con POST, GET paginado,
GET por id, PATCH parcial y DELETE. Reutiliza el modelo y la tabla `operador`
de `0001`, cuya existencia y restricciones se comprobaron antes de implementar.
No se modificaron tablas, migraciones ni Angular.

Consulta el [README principal](../README.md#crud-de-operadores-solo-backend)
para contratos, reglas, ejemplo de `/docs`, comandos PowerShell del entorno
virtual existente, resultados comprobados y verificaciones pendientes.

## Administración de celdas

El administrador puede crear, consultar, buscar por código exacto, editar y eliminar celdas. Código normalizado en mayúsculas y único. Los tipos admitidos son Automóviles y camionetas y Motocicletas. Las restricciones de PostgreSQL impiden duplicados simultáneos y eliminar celdas con estancias abiertas o cerradas.

- GET `/celdas` admite `codigo`, `offset` y `limit`.
- POST `/celdas` devuelve 201 o 409 por código duplicado.
- GET y PATCH `/celdas/{id}` devuelven 200 o 404 si no existe.
- DELETE `/celdas/{id}` devuelve 204, 404 o 409 si tiene historial.
- Los cuerpos inválidos devuelven 422. Un operador recibe 403 en estas rutas y una solicitud sin sesión recibe 401.

`configurar_celdas.py` prepara los 80 espacios iniciales. Es una herramienta de instalación y requiere revisar códigos ajenos a ese conjunto antes de ejecutarse sobre un catálogo personalizado.
## Preparar el entorno

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.txt` fija todas las dependencias de la aplicacion, incluidas
las transitivas. No es necesario activar el entorno virtual.

## Ejecutar la API

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

`GET http://127.0.0.1:8000/health` devuelve `{"status": "ok"}` con estado HTTP 200.
La documentación interactiva está en `http://127.0.0.1:8000/docs`.

## PostgreSQL local

1. Instala e inicia PostgreSQL localmente y prepara una base de datos y un usuario.
   Este proyecto no instala PostgreSQL ni crea bases de datos. Las tablas se crean
   únicamente cuando ejecutas explícitamente las migraciones descritas más abajo.
2. Si no existe `.env`, copia la plantilla sin sobrescribir un archivo existente:

   ```powershell
   if (-not (Test-Path -LiteralPath .env)) {
       Copy-Item -LiteralPath .env.example -Destination .env
   }
   ```

3. Edita `.env` localmente. Completa `DB_NAME`, `DB_USER` y `DB_PASSWORD`.
   Confirma `DB_HOST` y `DB_PORT` (ejemplos: `127.0.0.1` y `5432`).
   `DB_CONNECT_TIMEOUT` es un entero entre 1 y 60 segundos.
   Los valores `CAMBIAR_...` son marcadores: no permiten intentar una conexión.
   Si la contraseña contiene espacios o `#`, usa comillas simples en `.env`.
   No se interpolan expresiones `${...}` dentro de los valores.
4. Comprueba la conexión:

   ```powershell
   .\.venv\Scripts\python.exe .\check_db.py
   $LASTEXITCODE
   ```

El comando solo ejecuta `SELECT 1`, sin crear ni modificar tablas. Devuelve 0
únicamente tras verificar una respuesta real; 2 si faltan variables o son
inválidas; 1 si la conexión o la consulta fallan. No imprime credenciales, URL
de conexión ni detalles del controlador que pudieran contener datos privados.

Desde cualquier carpeta puedes usar rutas absolutas:

```powershell
& 'C:\Users\user\Documents\IU DIGITAL\Clase Ingeniería de Software\AutosColombia\backend\.venv\Scripts\python.exe' 'C:\Users\user\Documents\IU DIGITAL\Clase Ingeniería de Software\AutosColombia\backend\check_db.py'
```

`app/config.py` localiza `.env` respecto a su propio archivo, independientemente
de la carpeta de ejecución. Las variables de entorno tienen prioridad sobre
`.env`. Reinicia los procesos después de cambiar la configuración.

`app/database.py` proporciona `get_engine()` y la dependencia `get_session()`
para futuros endpoints. No conecta al importar ni ejecuta `create_all` o
migraciones. `/health` sigue comprobando la API, no PostgreSQL, y funciona sin
configurar la base de datos.
`.env` está excluido de Git. `.env.example` se conserva como plantilla pública;
nunca copies contraseñas reales a ella.

## Modelos y migración inicial

Los modelos están en `app/models.py`, separados de la conexión (`app/database.py`)
y de la configuración (`app/config.py`). La revisión `0001`, en
`migrations/versions/0001_modelos_iniciales.py`, crea estas tablas:

| Clase | Tabla | Atributos |
| --- | --- | --- |
| Vehiculo | vehiculo | id, placa, color, modelo, marca, tipo |
| Celda | celda | id, codigo, tipo |
| Operador | operador | id, nombre, telefono |

- `id` usa `BIGINT GENERATED ALWAYS AS IDENTITY` y clave primaria. Se omite al insertar.
- Todos los campos son `NOT NULL`. Los textos tienen comprobaciones contra valores
  vacíos o formados únicamente por espacios, tabulaciones o saltos de línea.
- El ORM elimina espacios exteriores y convierte `placa` y `codigo` a mayúsculas,
  tanto al construir objetos como al asignar estos atributos. PostgreSQL exige
  esa forma normalizada mediante `CHECK` y garantiza su unicidad con `UNIQUE`.
  SQL directo y operaciones masivas que omiten validadores deben normalizar antes;
  la base rechaza valores sin normalizar en lugar de transformarlos silenciosamente.
- `modelo` es un año entero entre 1 y 9999, no un nombre comercial; no se impone
  un límite vinculado al año actual. `telefono` es texto y conserva prefijos y ceros.
- El tipo de vehículo admite únicamente `MOTO`, `AUTOMOVIL` y `CAMIONETA`.
  El tipo de celda es texto no vacío, sin catálogo ni reglas de compatibilidad todavía.
- La revisión `0001` no tenía relaciones. `0002` añadió Estancia y `0003`
  agrega clientes y la asociación opcional con vehículos. FastAPI no crea
  tablas al iniciar y `/health` conserva su funcionamiento independiente.

Al preparar esta revisión no se encontraron tablas de usuario ni revisiones
anteriores. Al implementar el CRUD se verificó que la revisión **0001 ya estaba
aplicada en autos_colombia**; no se modificó ni se volvió a aplicar.
Alembic reutiliza `backend/.env` y no almacena una URL con credenciales en su INI.

### Instalar y revisar sin modificar PostgreSQL

```powershell
Set-Location -LiteralPath 'C:\Users\user\Documents\IU DIGITAL\Clase Ingeniería de Software\AutosColombia\backend'
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe .\check_db.py
.\.venv\Scripts\python.exe -m alembic -c .\alembic.ini history
.\.venv\Scripts\python.exe -m alembic -c .\alembic.ini heads
Get-Content -LiteralPath .\migrations\versions\0001_modelos_iniciales.py
.\.venv\Scripts\python.exe -m alembic -c .\alembic.ini upgrade head --sql
```

El último comando **solo imprime SQL**: no conecta a PostgreSQL ni aplica cambios.
Incluye las cinco tablas y `alembic_version`, que Alembic utiliza para registrar
las revisiones aplicadas.
### Aplicar después de revisar (estos comandos sí modifican el esquema)

Ejecuta este bloque únicamente cuando decidas aplicar la migración:

```powershell
Set-Location -LiteralPath 'C:\Users\user\Documents\IU DIGITAL\Clase Ingeniería de Software\AutosColombia\backend'
.\.venv\Scripts\python.exe .\check_db.py
if ($LASTEXITCODE -ne 0) { throw 'La conexión no está disponible; no aplicar migraciones.' }
.\.venv\Scripts\python.exe -m alembic -c .\alembic.ini upgrade head
if ($LASTEXITCODE -ne 0) { throw 'La migración no se completó; revisar el esquema antes de continuar.' }
.\.venv\Scripts\python.exe -m alembic -c .\alembic.ini current
```

El resultado esperado de `current` después de aplicar toda la cadena es `0006 (head)`.
No uses `stamp` para dar por aplicada una migración que no se ejecutó. Si ya hay
tablas con los mismos nombres, detente y revisa su estructura: esta migración no
las borra ni las recrea y fallará ante un conflicto. Su `downgrade` elimina las
tres tablas y sus datos; no lo ejecutes como parte de la instalación.

Los paths de Alembic se resuelven respecto a `alembic.ini`. Desde otra carpeta,
utiliza rutas absolutas para el intérprete y `-c`, igual que con `check_db.py`.

## CRUD de vehículos

La implementación se divide en `app/schemas/vehiculo.py` (validación y respuestas),
`app/routers/vehiculos.py` (APIRouter) y `app/services/vehiculo.py` (operaciones y
transacciones). Reutiliza el modelo `Vehiculo`, `get_session()` y las tablas existentes.

| Método y ruta | Resultado |
| --- | --- |
| `POST /vehiculos` | 201 y vehículo registrado, incluido su id |
| `GET /vehiculos?offset=0&limit=20` | 200 con `items`, `total`, `offset` y `limit` |
| `GET /vehiculos/{id}` | 200 y vehículo, o 404 |
| `PATCH /vehiculos/{id}` | 200 y vehículo actualizado, o 404 |
| `DELETE /vehiculos/{id}` | 204 sin cuerpo, o 404 |

La lista se ordena por id ascendente; `offset` empieza en 0 y `limit` admite de
1 a 100 (20 por defecto). `total` es el número total de vehículos, no solo el de
la página. Los ids deben ser enteros positivos dentro del rango de BIGINT.

Al crear se requieren placa, color, modelo, marca y tipo; `cliente_id` es
opcional y debe referenciar un cliente existente. El año debe ser un
entero JSON entre 1 y 9999; no se aceptan cadenas, booleanos ni decimales. Los
textos no pueden estar vacíos. La placa se recorta y se convierte a mayúsculas.
Los tipos admitidos son `MOTO`, `AUTOMOVIL` y `CAMIONETA`.

PATCH aplica solo los campos enviados, rechaza valores nulos (excepto
`cliente_id: null`, que quita la asociación) y campos desconocidos, incluido `id`.
Un objeto vacío conserva el vehículo. Los errores de validación
devuelven 422, una placa duplicada devuelve 409 y un vehículo inexistente, 404.
La unicidad se comprueba en PostgreSQL, también ante peticiones concurrentes;
las transacciones fallidas se revierten. Una clave foránea que impida borrar
devuelve 409 sin eliminar registros relacionados. No hay borrado en cascada en
el servicio. Los fallos generales de base de datos devuelven 503 sin detalles privados.

### Probar desde /docs

Inicia o reinicia el servidor para cargar las nuevas rutas:

```powershell
Set-Location -LiteralPath 'C:\Users\user\Documents\IU DIGITAL\Clase Ingeniería de Software\AutosColombia\backend'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Abre <http://127.0.0.1:8000/docs>, despliega **Vehículos** y usa **Try it out**.
Crea un vehículo con POST, copia el id devuelto y úsalo para GET, PATCH y DELETE.
Repite el POST con la misma placa para comprobar 409; prueba PATCH con
`{"color": null}` para comprobar 422. Después de borrar el registro, GET devuelve
404. Estas acciones desde `/docs` sí guardan cambios en tu base.

### Probar desde otra terminal de PowerShell

Este ejemplo crea una placa de prueba aleatoria y elimina solo el vehículo que
acaba de crear. Mantén el backend en ejecución en la primera terminal.

```powershell
$apiUrl = 'http://127.0.0.1:8000'
$testPlate = 'TEST-' + [guid]::NewGuid().ToString('N').Substring(0, 12).ToUpperInvariant()
$payload = @{
    placa = $testPlate
    color = 'Azul'
    modelo = 2025
    marca = 'Prueba'
    tipo = 'AUTOMOVIL'
} | ConvertTo-Json
$vehicle = Invoke-RestMethod -Method Post -Uri "$apiUrl/vehiculos" -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($payload))
try {
    $vehicle
    Invoke-RestMethod -Uri "$apiUrl/vehiculos?offset=0&limit=20"
    Invoke-RestMethod -Uri "$apiUrl/vehiculos/$($vehicle.id)"
    Invoke-RestMethod -Method Patch -Uri "$apiUrl/vehiculos/$($vehicle.id)" -ContentType 'application/json' -Body '{"color":"Rojo"}'
} finally {
    $response = Invoke-WebRequest -Method Delete -Uri "$apiUrl/vehiculos/$($vehicle.id)" -UseBasicParsing
    $response.StatusCode # 204
}
```

### Verificación manual

Esta entrega no incluye suites automatizadas. Verifica la conexión con
`check_db.py`, las dependencias con `python -m pip check` usando `.venv`, y las
operaciones desde la aplicación o `/docs`. No se han cambiado las validaciones
de negocio ni las restricciones de la base al retirar las pruebas.
