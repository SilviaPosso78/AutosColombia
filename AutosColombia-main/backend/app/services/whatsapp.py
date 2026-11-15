import re
from dataclasses import dataclass, field
from datetime import date
import os

from dotenv import dotenv_values
import httpx

from app.config import ENV_FILE


@dataclass(frozen=True)
class WhatsAppSettings:
    enabled: bool
    version: str
    phone_id: str = field(repr=False)
    token: str = field(repr=False)
    template: str
    language: str
    app_secret: str = field(repr=False)
    verify_token: str = field(repr=False)

    @property
    def faltantes(self) -> list[str]:
        requeridos = {
            "WHATSAPP_PHONE_NUMBER_ID": self.phone_id,
            "WHATSAPP_ACCESS_TOKEN": self.token,
            "WHATSAPP_TEMPLATE_NAME": self.template,
            "WHATSAPP_APP_SECRET": self.app_secret,
            "WHATSAPP_VERIFY_TOKEN": self.verify_token,
        }
        faltantes = [key for key, value in requeridos.items() if not value or value.startswith("CAMBIAR_")]
        if not re.fullmatch(r"v\d+\.\d+", self.version):
            faltantes.append("WHATSAPP_API_VERSION")
        if self.phone_id and not self.phone_id.isdigit() and "WHATSAPP_PHONE_NUMBER_ID" not in faltantes:
            faltantes.append("WHATSAPP_PHONE_NUMBER_ID")
        return faltantes


def configuracion_whatsapp() -> WhatsAppSettings:
    values = {**dotenv_values(ENV_FILE, encoding="utf-8-sig", interpolate=False), **os.environ}
    return WhatsAppSettings(
        enabled=(values.get("WHATSAPP_ENABLED") or "false").lower() == "true",
        version=values.get("WHATSAPP_API_VERSION") or "v27.0",
        phone_id=values.get("WHATSAPP_PHONE_NUMBER_ID") or "",
        token=values.get("WHATSAPP_ACCESS_TOKEN") or "",
        template=values.get("WHATSAPP_TEMPLATE_NAME") or "",
        language=values.get("WHATSAPP_TEMPLATE_LANGUAGE") or "es",
        app_secret=values.get("WHATSAPP_APP_SECRET") or "",
        verify_token=values.get("WHATSAPP_VERIFY_TOKEN") or "",
    )


def telefono_whatsapp(value: str | None) -> str | None:
    numero = re.sub(r"[\s()+.-]", "", value or "")
    if re.fullmatch(r"3\d{9}", numero):
        numero = "57" + numero
    elif len(numero) <= 10 and not (value or "").strip().startswith("+"):
        return None
    return numero if re.fullmatch(r"[1-9]\d{7,14}", numero) else None


def texto_recordatorio(nombre: str, placa: str, fin: date) -> str:
    return (
        f"Hola {nombre}. Autos Colombia te recuerda que la mensualidad del vehículo "
        f"{placa} vence el {fin.strftime('%d/%m/%Y')} inclusive. "
        "Puedes renovar tu mensualidad en el parqueadero. Gracias."
    )


class EnvioError(Exception):
    def __init__(self, estado: str, detalle: str) -> None:
        self.estado = estado
        self.detalle = detalle


def enviar_plantilla(settings: WhatsAppSettings, payload: dict) -> str:
    try:
        response = httpx.post(
            f"https://graph.facebook.com/{settings.version}/{settings.phone_id}/messages",
            headers={"Authorization": f"Bearer {settings.token}"},
            json=payload, timeout=15,
        )
    except httpx.TransportError:
        raise EnvioError("REVISION", "No se pudo confirmar el resultado del envío. Revisa WhatsApp Business antes de volver a enviarlo.") from None
    if response.status_code >= 400:
        raise EnvioError("ERROR", f"WhatsApp Business rechazó el envío (HTTP {response.status_code}). Revisa la configuración y la plantilla.")
    try:
        mensaje_id = response.json()["messages"][0]["id"]
        if not isinstance(mensaje_id, str) or not mensaje_id:
            raise ValueError
        return mensaje_id
    except (ValueError, KeyError, IndexError, TypeError):
        raise EnvioError("REVISION", "WhatsApp no devolvió una confirmación reconocible. Revisa el envío antes de repetirlo.") from None
