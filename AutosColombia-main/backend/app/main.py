import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routers.vehiculos import router as vehiculos_router
from app.services.vehiculo import VehiculoError
from app.routers.celdas import router as celdas_router
from app.services.celda import CeldaError
from app.routers.operadores import router as operadores_router
from app.services.operador import OperadorError
from app.routers.clientes import router as clientes_router
from app.services.cliente import ClienteError
from app.routers.estancias import router as estancias_router
from app.services.estancia import EstanciaError
from app.routers.pagos import router as pagos_router
from app.routers.notificaciones import router as notificaciones_router
from app.services.pago import PagoError
from app.services.notificacion import ejecutar_avisos
from app.routers.auth import router as auth_router, usuarios_router
from app.services.auth import administrador, operador

@asynccontextmanager
async def lifespan(app: FastAPI):
    worker = asyncio.create_task(ejecutar_avisos())
    try:
        yield
    finally:
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker


app = FastAPI(title="Autos Colombia API", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(usuarios_router)
app.include_router(vehiculos_router, dependencies=[Depends(operador)])
app.include_router(celdas_router, dependencies=[Depends(administrador)])
app.include_router(operadores_router)
app.include_router(clientes_router, dependencies=[Depends(operador)])
app.include_router(estancias_router, dependencies=[Depends(operador)])
app.include_router(pagos_router, dependencies=[Depends(operador)])
app.include_router(notificaciones_router)


@app.middleware("http")
async def private_responses(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    # Las respuestas de validación nunca reproducen contraseñas, cookies ni cuerpos recibidos.
    details = [{key: value for key, value in item.items() if key in {"loc", "msg", "type"}}
               for item in error.errors()]
    return JSONResponse(status_code=422, content={"detail": details})


@app.exception_handler(VehiculoError)
@app.exception_handler(CeldaError)
@app.exception_handler(OperadorError)
@app.exception_handler(ClienteError)
@app.exception_handler(EstanciaError)
@app.exception_handler(PagoError)
async def entity_error_handler(request, error: VehiculoError | CeldaError | OperadorError | ClienteError | EstanciaError | PagoError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"detail": error.detail})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
