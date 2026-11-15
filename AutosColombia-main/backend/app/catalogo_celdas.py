"""Catálogo fijo del parqueadero y preparación explícita de sus registros."""

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Celda

TIPO_CARRO = "Automóviles y camionetas"
TIPO_MOTO = "Motocicletas"
CELDAS_FIJAS = {
    **{f"C{numero:02d}": TIPO_CARRO for numero in range(1, 71)},
    **{f"M{numero:02d}": TIPO_MOTO for numero in range(1, 11)},
}
CATALOGO_FIJO = (
    "El catálogo es fijo: C01 a C70 para automóviles y camionetas, "
    "M01 a M10 para motocicletas. No se permite crear, modificar ni eliminar celdas."
)


def configurar_catalogo(session: Session) -> None:
    """Completa las 80 celdas en una transacción, conservando ids e historial."""
    with session.begin():
        # Serializa preparaciones simultáneas y evita cambios parciales del catálogo.
        session.execute(text("LOCK TABLE celda IN EXCLUSIVE MODE"))
        existentes = {celda.codigo: celda for celda in session.scalars(select(Celda))}
        anterior = existentes.pop("CD025", None)
        if anterior is not None:
            if "C25" in existentes:
                raise ValueError("Existen CD025 y C25. Revisa su correspondencia antes de configurar.")
            anterior.codigo = "C25"
            existentes["C25"] = anterior
        if set(existentes) - CELDAS_FIJAS.keys():
            raise ValueError("Hay códigos fuera del catálogo fijo. Revisa su correspondencia física.")
        for codigo, tipo in CELDAS_FIJAS.items():
            celda = existentes.get(codigo)
            if celda is None:
                session.add(Celda(codigo=codigo, tipo=tipo))
            else:
                celda.tipo = tipo
        session.flush()
