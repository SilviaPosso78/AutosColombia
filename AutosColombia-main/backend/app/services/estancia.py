from datetime import datetime, timezone
from functools import wraps

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Celda, Estancia, Operador, Tiquete, Vehiculo, required_text
from app.catalogo_celdas import TIPO_CARRO, TIPO_MOTO
from app.schemas.celda import CeldaRespuesta
from app.schemas.estancia import (
    EntradaCrear, SalidaCrear, EstanciaRespuesta, EstanciaAbiertaRespuesta,
    EstadoVehiculoRespuesta,
    OcupacionCeldaRespuesta,
    EntradaRegistrada,
)
from app.schemas.tiquete import TiqueteRespuesta
from app.schemas.vehiculo import VehiculoRespuesta
from app.services.pago import exigir_mensualidad


class EstanciaError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def transaccion(operation):
    """Una transacción por solicitud; materializa la respuesta antes del commit."""
    @wraps(operation)
    def wrapped(self, *args, **kwargs):
        try:
            with self.session.begin():
                return operation(self, *args, **kwargs)
        except IntegrityError as error:
            self.session.rollback()
            code = getattr(error.orig, "sqlstate", None)
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if code == "23505":
                if constraint == "uq_estancia_vehiculo_abierta":
                    raise EstanciaError(409, "El vehículo ya está dentro.") from None
                if constraint == "uq_estancia_celda_abierta":
                    raise EstanciaError(409, "La celda está ocupada.") from None
            if code == "23503":
                raise EstanciaError(404, "Una de las referencias ya no existe. Actualiza los datos.") from None
            if code in {"23502", "23514"}:
                raise EstanciaError(422, "Los datos incumplen las restricciones de la estancia.") from None
            raise EstanciaError(409, "La operación entra en conflicto con los datos existentes.") from None
        except SQLAlchemyError:
            self.session.rollback()
            raise EstanciaError(503, "No se pudo completar la operación con la base de datos.") from None
    return wrapped


def respuesta_tiquete(estancia: Estancia, tiquete: Tiquete) -> TiqueteRespuesta:
    return TiqueteRespuesta(
        numero=f"AC-{estancia.id:08d}", estancia_id=estancia.id,
        placa=tiquete.placa, tipo_vehiculo=tiquete.tipo_vehiculo,
        entrada=estancia.entrada, celda_codigo=tiquete.celda_codigo, puerta=tiquete.puerta,
        operador_id=estancia.operador_entrada_id, operador_nombre=tiquete.operador_entrada_nombre,
        reconstruido=tiquete.reconstruido,
    )


class ServicioEstancia:
    def __init__(self, session: Session) -> None:
        self.session = session

    @transaccion
    def ocupacion(self) -> list[OcupacionCeldaRespuesta]:
        rows = self.session.execute(
            select(Celda, Estancia, Vehiculo.placa)
            .outerjoin(Estancia, and_(Estancia.celda_id == Celda.id, Estancia.salida.is_(None)))
            .outerjoin(Vehiculo, Vehiculo.id == Estancia.vehiculo_id)
            .order_by(Celda.codigo)
        ).all()
        return [
            OcupacionCeldaRespuesta(
                **CeldaRespuesta.model_validate(celda).model_dump(),
                ocupada=estancia is not None,
                placa=placa,
                entrada=estancia.entrada if estancia is not None else None,
            )
            for celda, estancia, placa in rows
        ]

    def _vehiculo(self, placa: str) -> Vehiculo:
        vehiculo = self.session.scalar(select(Vehiculo).where(Vehiculo.placa == placa))
        if vehiculo is None:
            raise EstanciaError(404, "Vehículo no encontrado.")
        return vehiculo

    def _operador(self, operador_id: int) -> Operador:
        operador = self.session.get(Operador, operador_id)
        if operador is None:
            raise EstanciaError(404, "Operador no encontrado.")
        return operador

    @transaccion
    def entrada(self, data: EntradaCrear) -> EntradaRegistrada:
        vehiculo = self._vehiculo(data.placa)
        if vehiculo.cliente_id is None:
            raise EstanciaError(409, "Asocia el vehículo con su cliente responsable antes de registrar la entrada.")
        celda = self.session.get(Celda, data.celda_id)
        if celda is None:
            raise EstanciaError(404, "Celda no encontrada.")
        operador = self._operador(data.operador_id)
        tipo_esperado = TIPO_MOTO if vehiculo.tipo == "MOTO" else TIPO_CARRO
        tipo_celda = celda.tipo
        if tipo_celda != tipo_esperado:
            raise EstanciaError(
                409,
                f"El vehículo {vehiculo.placa} es de tipo {vehiculo.tipo}. "
                f"Selecciona una celda de {tipo_esperado.lower()}.",
            )
        if self.session.scalar(select(Estancia.id).where(
            Estancia.vehiculo_id == vehiculo.id, Estancia.salida.is_(None)
        )) is not None:
            raise EstanciaError(409, "El vehículo ya está dentro.")
        if self.session.scalar(select(Estancia.id).where(
            Estancia.celda_id == celda.id, Estancia.salida.is_(None)
        )) is not None:
            raise EstanciaError(409, "La celda está ocupada.")
        exigir_mensualidad(self.session, vehiculo.id)
        estancia = Estancia(vehiculo_id=vehiculo.id, celda_id=celda.id,
                            operador_entrada_id=operador.id, entrada=datetime.now(timezone.utc))
        self.session.add(estancia)
        # Los índices únicos deciden también cuando dos solicitudes superan las consultas previas.
        self.session.flush()
        tiquete = Tiquete(
            estancia_id=estancia.id, placa=vehiculo.placa, tipo_vehiculo=vehiculo.tipo,
            celda_codigo=celda.codigo, puerta="Entrada", operador_entrada_nombre=operador.nombre,
            reconstruido=False,
        )
        self.session.add(tiquete)
        self.session.flush()
        return EntradaRegistrada(
            **EstanciaRespuesta.model_validate(estancia).model_dump(),
            tiquete=respuesta_tiquete(estancia, tiquete),
        )

    @transaccion
    def salida(self, data: SalidaCrear) -> EstanciaRespuesta:
        vehiculo = self._vehiculo(data.placa)
        operador = self._operador(data.operador_id)
        # PostgreSQL vuelve a evaluar salida IS NULL tras esperar el bloqueo.
        estancia = self.session.scalar(select(Estancia).where(
            Estancia.vehiculo_id == vehiculo.id, Estancia.salida.is_(None)
        ).with_for_update())
        if estancia is None:
            raise EstanciaError(409, "El vehículo no tiene una estancia abierta.")
        exigir_mensualidad(self.session, vehiculo.id)
        tiquete = self.session.get(Tiquete, estancia.id)
        if tiquete is None:
            raise EstanciaError(409, "No se encontró el tiquete de la estancia. Actualiza el historial antes de registrar la salida.")
        try:
            estancia.cerrar(datetime.now(timezone.utc), operador)
        except ValueError:
            raise EstanciaError(409, "No se puede cerrar la estancia con su estado o fecha actuales.") from None
        tiquete.operador_salida_nombre = operador.nombre
        self.session.flush()
        return EstanciaRespuesta.model_validate(estancia)

    @transaccion
    def consultar(self, placa: str) -> EstadoVehiculoRespuesta:
        placa = required_text(placa, "placa").upper()
        # Una sola consulta da un estado consistente de vehículo, estancia y celda.
        row = self.session.execute(select(Vehiculo, Estancia, Celda).outerjoin(
            Estancia, and_(Estancia.vehiculo_id == Vehiculo.id, Estancia.salida.is_(None))
        ).outerjoin(Celda, Celda.id == Estancia.celda_id).where(Vehiculo.placa == placa)).one_or_none()
        if row is None:
            raise EstanciaError(404, "Vehículo no encontrado.")
        vehiculo, estancia, celda = row
        abierta = None
        if estancia is not None:
            abierta = EstanciaAbiertaRespuesta(
                **EstanciaRespuesta.model_validate(estancia).model_dump(),
                celda=CeldaRespuesta.model_validate(celda),
            )
        return EstadoVehiculoRespuesta(vehiculo=VehiculoRespuesta.model_validate(vehiculo),
                                       esta_dentro=estancia is not None, estancia=abierta)
