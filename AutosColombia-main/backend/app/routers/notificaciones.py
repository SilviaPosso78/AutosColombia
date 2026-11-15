import hashlib
import hmac
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas.notificacion import AvisosPagina, ConfiguracionAvisos
from app.services.notificacion import ServicioNotificacion, registrar_estados
from app.services.whatsapp import configuracion_whatsapp
from app.services.auth import operador

router = APIRouter(prefix="/notificaciones", tags=["Avisos de mensualidad"])
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.get("/configuracion", response_model=ConfiguracionAvisos, dependencies=[Depends(operador)])
def configuracion() -> ConfiguracionAvisos:
    settings = configuracion_whatsapp()
    return ConfiguracionAvisos(habilitado=settings.enabled, configurado=not settings.faltantes, faltantes=settings.faltantes)


@router.get("", response_model=AvisosPagina, dependencies=[Depends(operador)])
def listar(session: DatabaseSession, offset: Annotated[int, Query(ge=0)] = 0,
           limit: Annotated[int, Query(ge=1, le=100)] = 10) -> AvisosPagina:
    return ServicioNotificacion(session).listar(offset, limit)


@router.post("/{aviso_id}/reintentar", dependencies=[Depends(operador)])
def reintentar(aviso_id: int, session: DatabaseSession) -> dict[str, str]:
    return ServicioNotificacion(session).reintentar(aviso_id)


@router.get("/webhook", response_class=PlainTextResponse)
def verificar_webhook(request: Request) -> str:
    settings = configuracion_whatsapp()
    query = request.query_params
    if settings.verify_token and query.get("hub.mode") == "subscribe" and hmac.compare_digest(
        query.get("hub.verify_token", ""), settings.verify_token
    ):
        return query.get("hub.challenge", "")
    raise HTTPException(403, "No se pudo verificar el webhook.")


@router.post("/webhook")
async def webhook(request: Request, session: DatabaseSession) -> dict[str, str]:
    settings = configuracion_whatsapp()
    body = await request.body()
    esperado = "sha256=" + hmac.new(settings.app_secret.encode(), body, hashlib.sha256).hexdigest()
    if not settings.app_secret or not hmac.compare_digest(request.headers.get("x-hub-signature-256", ""), esperado):
        raise HTTPException(403, "Firma de webhook inválida.")
    try:
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError
        registrar_estados(session, payload)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(400, "Notificación no reconocida.") from None
    except SQLAlchemyError:
        raise HTTPException(503, "No se pudo guardar la confirmación. Meta puede reintentarla.") from None
    return {"status": "ok"}
