from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas.pago import EstadoMensualidad, MensualidadesPagina, PagoCrear, PagoRespuesta, PagosPagina
from app.services.pago import ServicioPago
from app.services.auth import UsuarioActual

router = APIRouter(tags=["Pagos y mensualidades"])
DatabaseSession = Annotated[Session, Depends(get_session)]
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]


@router.post("/pagos", response_model=PagoRespuesta, status_code=201)
def registrar(data: PagoCrear, session: DatabaseSession, usuario: UsuarioActual) -> PagoRespuesta:
    if data.operador_id != usuario.operador_id:
        raise HTTPException(403, "El pago debe identificar al operador de la sesión.")
    return ServicioPago(session).registrar(data)


@router.get("/pagos", response_model=PagosPagina)
def historial(session: DatabaseSession, placa: str | None = None, offset: Offset = 0, limit: Limit = 10) -> PagosPagina:
    return ServicioPago(session).historial(placa, offset, limit)


@router.get("/mensualidades", response_model=MensualidadesPagina)
def mensualidades(session: DatabaseSession, placa: str | None = None, estado: EstadoMensualidad | None = None,
                   offset: Offset = 0, limit: Limit = 10) -> MensualidadesPagina:
    return ServicioPago(session).mensualidades(placa, estado, offset, limit)
