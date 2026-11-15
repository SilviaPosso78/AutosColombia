import asyncio
from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_engine
from app.models import AvisoMensualidad, Cliente, Pago, Vehiculo
from app.schemas.notificacion import AvisoRespuesta, AvisosPagina
from app.services.pago import PagoError, hoy_bogota, transaccion
from app.services.whatsapp import (
    EnvioError, WhatsAppSettings, configuracion_whatsapp, enviar_plantilla,
    telefono_whatsapp, texto_recordatorio,
)

logger = logging.getLogger(__name__)


class ServicioNotificacion:
    def __init__(self, session: Session) -> None:
        self.session = session

    @transaccion
    def listar(self, offset: int, limit: int) -> AvisosPagina:
        consulta = select(AvisoMensualidad, Pago, Vehiculo, Cliente).join(
            Pago, Pago.id == AvisoMensualidad.pago_id
        ).join(Vehiculo, Vehiculo.id == Pago.vehiculo_id).join(Cliente, Cliente.id == Pago.cliente_id)
        total = self.session.scalar(select(func.count()).select_from(consulta.subquery()))
        filas = self.session.execute(consulta.order_by(
            AvisoMensualidad.programado_para.desc(), AvisoMensualidad.id.desc()
        ).offset(offset).limit(limit)).all()
        return AvisosPagina(items=[AvisoRespuesta(
            id=aviso.id, pago_id=pago.id, placa=vehiculo.placa, cliente_nombre=cliente.nombre,
            telefono=aviso.destinatario or telefono_whatsapp(cliente.telefono),
            programado_para=aviso.programado_para, fin=pago.fin, dias_antes=aviso.dias_antes,
            estado=aviso.estado, detalle=aviso.detalle, enviado_en=aviso.enviado_en,
            texto=texto_recordatorio(cliente.nombre, vehiculo.placa, pago.fin),
        ) for aviso, pago, vehiculo, cliente in filas], total=total, offset=offset, limit=limit)

    @transaccion
    def reintentar(self, aviso_id: int) -> dict[str, str]:
        aviso = self.session.scalar(select(AvisoMensualidad).where(AvisoMensualidad.id == aviso_id).with_for_update())
        if aviso is None:
            raise PagoError(404, "Aviso no encontrado.")
        if aviso.estado != "ERROR":
            raise PagoError(409, "Solo se pueden reintentar automáticamente avisos rechazados por WhatsApp.")
        if aviso.programado_para != hoy_bogota():
            raise PagoError(409, "La fecha de este aviso ya pasó o todavía no ha llegado.")
        aviso.estado = "PENDIENTE"
        aviso.detalle = None
        aviso.mensaje_id = None
        return {"detail": "Aviso programado para reintentar en el siguiente ciclo."}


def preparar_aviso(session: Session, settings: WhatsAppSettings) -> tuple[int, dict | None] | None:
    hoy = hoy_bogota()
    with session.begin():
        session.execute(update(AvisoMensualidad).where(
            AvisoMensualidad.estado == "EN_PROCESO",
            AvisoMensualidad.intento_en < datetime.now(timezone.utc) - timedelta(minutes=5),
        ).values(estado="REVISION", detalle="El proceso se interrumpió durante el envío. Revisa WhatsApp Business para comprobar el resultado."))
        aviso = session.scalar(select(AvisoMensualidad).where(
            AvisoMensualidad.estado == "PENDIENTE", AvisoMensualidad.programado_para <= hoy,
        ).order_by(AvisoMensualidad.programado_para, AvisoMensualidad.id).with_for_update(skip_locked=True).limit(1))
        if aviso is None:
            return None
        pago = session.get(Pago, aviso.pago_id)
        renovado = session.scalar(select(Pago.id).where(
            Pago.vehiculo_id == pago.vehiculo_id, Pago.inicio == pago.fin + timedelta(days=1),
        ).limit(1)) if pago.fin.year < 9999 else None
        if renovado is not None:
            aviso.estado = "CANCELADO"
            aviso.detalle = "La mensualidad ya fue renovada."
            return aviso.id, None
        if aviso.programado_para < hoy or pago.fin < hoy:
            aviso.estado = "OMITIDO"
            aviso.detalle = "La fecha programada del aviso ya pasó."
            return aviso.id, None
        vehiculo = session.get(Vehiculo, pago.vehiculo_id)
        cliente = session.get(Cliente, pago.cliente_id)
        telefono = telefono_whatsapp(cliente.telefono)
        if telefono is None:
            aviso.estado = "ERROR"
            aviso.detalle = "El cliente necesita un número de WhatsApp válido con indicativo de país."
            return aviso.id, None
        aviso.estado = "EN_PROCESO"
        aviso.intento_en = datetime.now(timezone.utc)
        aviso.destinatario = telefono
        payload = {
            "messaging_product": "whatsapp", "to": telefono, "type": "template",
            "biz_opaque_callback_data": f"aviso:{aviso.id}:{int(aviso.intento_en.timestamp() * 1000000)}",
            "template": {
                "name": settings.template, "language": {"code": settings.language},
                "components": [{"type": "body", "parameters": [
                    {"type": "text", "text": cliente.nombre},
                    {"type": "text", "text": vehiculo.placa},
                    {"type": "text", "text": pago.fin.strftime("%d/%m/%Y")},
                ]}],
            },
        }
        return aviso.id, payload


def procesar_avisos() -> int:
    settings = configuracion_whatsapp()
    if not settings.enabled or settings.faltantes:
        return 0
    enviados = 0
    for _ in range(100):
        with Session(get_engine()) as session:
            trabajo = preparar_aviso(session, settings)
        if trabajo is None:
            break
        aviso_id, payload = trabajo
        if payload is None:
            continue
        estado, detalle, mensaje_id = "ACEPTADO", None, None
        try:
            mensaje_id = enviar_plantilla(settings, payload)
            enviados += 1
        except EnvioError as error:
            estado, detalle = error.estado, error.detalle
        with Session(get_engine()) as session, session.begin():
            aviso = session.scalar(select(AvisoMensualidad).where(AvisoMensualidad.id == aviso_id).with_for_update())
            if aviso.estado == "EN_PROCESO":
                aviso.estado = estado
                aviso.detalle = detalle
            if mensaje_id:
                aviso.mensaje_id = mensaje_id
                aviso.enviado_en = datetime.now(timezone.utc)
    return enviados


async def ejecutar_avisos() -> None:
    while True:
        try:
            await asyncio.to_thread(procesar_avisos)
        except (SQLAlchemyError, ValueError, OSError):
            logger.warning("No se pudo completar el ciclo de avisos. Se revisará en el siguiente ciclo.")
        await asyncio.sleep(60)


def registrar_estados(session: Session, payload: dict) -> None:
    estados = {"sent": "ACEPTADO", "delivered": "ENTREGADO", "read": "LEIDO", "failed": "ERROR"}
    prioridad = {"PENDIENTE": 0, "EN_PROCESO": 0, "REVISION": 0, "ACEPTADO": 1, "ERROR": 2, "ENTREGADO": 3, "LEIDO": 4}
    with session.begin():
        for entrada in payload.get("entry", []):
            for cambio in entrada.get("changes", []):
                for status in cambio.get("value", {}).get("statuses", []):
                    nuevo = estados.get(status.get("status"))
                    if nuevo is None or not status.get("id"):
                        continue
                    consulta = select(AvisoMensualidad).where(AvisoMensualidad.mensaje_id == status["id"])
                    referencia = status.get("biz_opaque_callback_data", "")
                    partes = referencia.split(":") if isinstance(referencia, str) else []
                    if len(partes) == 3 and partes[0] == "aviso" and partes[1].isdigit() and partes[2].isdigit():
                        consulta = select(AvisoMensualidad).where(AvisoMensualidad.id == int(partes[1]))
                    aviso = session.scalar(consulta.with_for_update())
                    if aviso and len(partes) == 3:
                        if not aviso.intento_en or partes[2] != str(int(aviso.intento_en.timestamp() * 1000000)) or aviso.estado == "PENDIENTE":
                            continue
                    if aviso and aviso.mensaje_id and aviso.mensaje_id != status["id"]:
                        continue
                    if aviso and prioridad.get(nuevo, 0) >= prioridad.get(aviso.estado, 0):
                        aviso.estado = nuevo
                        aviso.mensaje_id = status["id"]
                        aviso.detalle = "WhatsApp informó un fallo de entrega. Revisa el número y la plantilla." if nuevo == "ERROR" else None
