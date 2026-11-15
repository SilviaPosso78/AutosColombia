from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas.estancia import EntradaCrear, EntradaRegistrada, SalidaCrear, EstanciaRespuesta, EstadoVehiculoRespuesta
from app.schemas.vehiculo import Placa
from app.services.estancia import ServicioEstancia
from app.schemas.estancia import OcupacionCeldaRespuesta
from app.schemas.tiquete import MovimientosPagina, TiqueteRespuesta
from app.services.tiquete import ServicioTiquete
from app.services.auth import UsuarioActual

router = APIRouter(prefix="/estancias", tags=["Estancias"])
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.get("/ocupacion", response_model=list[OcupacionCeldaRespuesta])
def ocupacion(session: DatabaseSession) -> list[OcupacionCeldaRespuesta]:
    return ServicioEstancia(session).ocupacion()


@router.post("/entrada", response_model=EntradaRegistrada, status_code=201)
def entrada(data: EntradaCrear, session: DatabaseSession, usuario: UsuarioActual) -> EntradaRegistrada:
    if data.operador_id != usuario.operador_id:
        raise HTTPException(403, "El movimiento debe identificar al operador de la sesión.")
    return ServicioEstancia(session).entrada(data)


@router.post("/salida", response_model=EstanciaRespuesta)
def salida(data: SalidaCrear, session: DatabaseSession, usuario: UsuarioActual) -> EstanciaRespuesta:
    if data.operador_id != usuario.operador_id:
        raise HTTPException(403, "El movimiento debe identificar al operador de la sesión.")
    return ServicioEstancia(session).salida(data)


@router.get("/vehiculo/{placa}", response_model=EstadoVehiculoRespuesta)
def consultar(placa: Placa, session: DatabaseSession) -> EstadoVehiculoRespuesta:
    return ServicioEstancia(session).consultar(placa)


@router.get("/tiquetes/{estancia_id}", response_model=TiqueteRespuesta)
def tiquete(estancia_id: Annotated[int, Path(ge=1, le=9223372036854775807)], session: DatabaseSession) -> TiqueteRespuesta:
    return ServicioTiquete(session).consultar(estancia_id)


@router.get("/movimientos", response_model=MovimientosPagina)
def movimientos(
    session: DatabaseSession, placa: str | None = None, desde: date | None = None, hasta: date | None = None,
    celda_id: Annotated[int | None, Query(ge=1, le=9223372036854775807)] = None,
    operador_id: Annotated[int | None, Query(ge=1, le=9223372036854775807)] = None,
    movimiento: Literal["ENTRADA", "SALIDA"] | None = None,
    offset: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> MovimientosPagina:
    return ServicioTiquete(session).movimientos(placa, desde, hasta, celda_id, operador_id, movimiento, offset, limit)
