from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import wraps
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, func, select, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import AvisoMensualidad, Cliente, Operador, Pago, Vehiculo
from app.schemas.pago import (
    MensualidadRespuesta, MensualidadesPagina, PagoCrear, PagoListado,
    PagoRespuesta, PagosPagina,
)

BOGOTA = ZoneInfo("America/Bogota")
TARIFAS_MENSUALES = {
    "AUTOMOVIL": Decimal("250000.00"),
    "CAMIONETA": Decimal("250000.00"),
    "MOTO": Decimal("100000.00"),
}


def hoy_bogota() -> date:
    return datetime.now(BOGOTA).date()


def sumar_mes(inicio: date) -> date:
    anio = inicio.year + (inicio.month == 12)
    mes = inicio.month % 12 + 1
    return date(anio, mes, min(inicio.day, monthrange(anio, mes)[1]))


class PagoError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def transaccion(operation):
    @wraps(operation)
    def wrapped(self, *args, **kwargs):
        try:
            with self.session.begin():
                return operation(self, *args, **kwargs)
        except IntegrityError:
            raise PagoError(409, "El pago entra en conflicto con los registros existentes. Actualiza antes de reintentar.") from None
        except SQLAlchemyError:
            raise PagoError(503, "No se pudo consultar o guardar la mensualidad. Comprueba la conexión y actualiza.") from None
    return wrapped


def capacidad_disponible(periodos: list[tuple[date, date]], inicio: date, fin: date, limite: int) -> bool:
    eventos: dict[int, int] = defaultdict(int)
    for desde, hasta in periodos:
        eventos[max(desde, inicio).toordinal()] += 1
        eventos[min(hasta, fin).toordinal() + 1] -= 1
    contratadas = 0
    for dia in sorted(eventos):
        contratadas += eventos[dia]
        if contratadas >= limite:
            return False
    return True


def exigir_mensualidad(session: Session, vehiculo_id: int) -> None:
    hoy = hoy_bogota()
    vigente = session.scalar(select(Pago.id).where(
        Pago.vehiculo_id == vehiculo_id, Pago.inicio <= hoy, Pago.fin >= hoy,
    ).limit(1))
    if vigente is None:
        raise PagoError(409, "El vehículo no tiene una mensualidad vigente. Registra el pago antes de continuar.")


class ServicioPago:
    def __init__(self, session: Session) -> None:
        self.session = session

    @transaccion
    def registrar(self, data: PagoCrear) -> PagoRespuesta:
        hoy = hoy_bogota()
        if data.fecha_pago > hoy:
            raise PagoError(422, "La fecha del pago no puede estar en el futuro.")
        # Serializa pagos para controlar también la capacidad de periodos futuros.
        self.session.execute(text("LOCK TABLE pago IN SHARE ROW EXCLUSIVE MODE"))
        vehiculo = self.session.scalar(select(Vehiculo).where(Vehiculo.placa == data.placa).with_for_update())
        if vehiculo is None:
            raise PagoError(404, "Vehículo no encontrado.")
        anterior = self.session.scalar(select(Pago).where(Pago.solicitud_id == data.solicitud_id))
        if anterior is not None:
            campos = data.model_dump(exclude={"solicitud_id", "placa"})
            if anterior.vehiculo_id != vehiculo.id or any(getattr(anterior, key) != value for key, value in campos.items()):
                raise PagoError(409, "Esta solicitud ya se usó para otro pago.")
            return PagoRespuesta.model_validate(anterior)
        tarifa = TARIFAS_MENSUALES[vehiculo.tipo]
        if data.valor != tarifa:
            valor_fijo = f"${tarifa:,.0f}".replace(",", ".")
            raise PagoError(422, f"La mensualidad para {vehiculo.tipo} tiene un valor fijo de {valor_fijo} COP.")
        if vehiculo.cliente_id is None:
            raise PagoError(409, "Asocia el vehículo con su cliente responsable antes de registrar el pago.")
        if self.session.get(Operador, data.operador_id) is None:
            raise PagoError(404, "Operador no encontrado.")
        solapado = self.session.scalar(select(Pago.id).where(
            Pago.vehiculo_id == vehiculo.id, Pago.inicio <= data.fin, Pago.fin >= data.inicio,
        ).limit(1))
        if solapado is not None:
            raise PagoError(409, "El periodo se cruza con una mensualidad ya pagada para este vehículo.")
        tipos = ["MOTO"] if vehiculo.tipo == "MOTO" else ["AUTOMOVIL", "CAMIONETA"]
        limite = 10 if vehiculo.tipo == "MOTO" else 70
        periodos = self.session.execute(select(Pago.inicio, Pago.fin).where(
            Pago.tipo_vehiculo.in_(tipos), Pago.inicio <= data.fin, Pago.fin >= data.inicio,
        )).all()
        if not capacidad_disponible(periodos, data.inicio, data.fin, limite):
            raise PagoError(409, f"Se alcanzó el límite de {limite} mensualidades para este tipo de vehículo en el periodo solicitado.")
        pago = Pago(
            **data.model_dump(exclude={"placa", "valor"}), valor=tarifa, vehiculo_id=vehiculo.id,
            cliente_id=vehiculo.cliente_id, tipo_vehiculo=vehiculo.tipo,
        )
        self.session.add(pago)
        self.session.flush()
        for dias in (5, 0):
            fecha = date.fromordinal(max(1, pago.fin.toordinal() - dias))
            self.session.add(AvisoMensualidad(
                pago_id=pago.id, dias_antes=dias, programado_para=fecha,
                estado="PENDIENTE" if fecha >= hoy else "OMITIDO",
                detalle=None if fecha >= hoy else "La fecha del aviso ya había pasado al registrar el pago.",
            ))
        anteriores = select(Pago.id).where(
            Pago.vehiculo_id == vehiculo.id, Pago.fin == data.inicio - timedelta(days=1),
        ) if data.inicio > date.min else select(Pago.id).where(Pago.id == -1)
        self.session.execute(update(AvisoMensualidad).where(
            AvisoMensualidad.pago_id.in_(anteriores),
            AvisoMensualidad.estado.in_(["PENDIENTE", "ERROR"]),
        ).values(estado="CANCELADO", detalle="La mensualidad ya fue renovada para el periodo siguiente."))
        self.session.flush()
        return PagoRespuesta.model_validate(pago)

    @transaccion
    def historial(self, placa: str | None, offset: int, limit: int) -> PagosPagina:
        consulta = select(Pago, Vehiculo.placa, Cliente.nombre, Operador.nombre).join(
            Vehiculo, Vehiculo.id == Pago.vehiculo_id
        ).join(Cliente, Cliente.id == Pago.cliente_id).join(Operador, Operador.id == Pago.operador_id)
        if placa:
            consulta = consulta.where(Vehiculo.placa == placa.strip().upper())
        total = self.session.scalar(select(func.count()).select_from(consulta.subquery()))
        filas = self.session.execute(consulta.order_by(Pago.creado_en.desc(), Pago.id.desc()).offset(offset).limit(limit)).all()
        return PagosPagina(items=[PagoListado(
            **PagoRespuesta.model_validate(pago).model_dump(), placa=numero,
            cliente_nombre=cliente, operador_nombre=operador,
        ) for pago, numero, cliente, operador in filas], total=total, offset=offset, limit=limit)

    @transaccion
    def mensualidades(self, placa: str | None, estado: str | None, offset: int, limit: int) -> MensualidadesPagina:
        hoy = hoy_bogota()
        activa = and_(Pago.inicio <= hoy, Pago.fin >= hoy)
        relevante = select(Pago.id).where(Pago.vehiculo_id == Vehiculo.id).order_by(
            case((activa, 0), (Pago.inicio > hoy, 1), else_=2),
            case((Pago.inicio > hoy, Pago.inicio)).asc().nullslast(), Pago.fin.desc(),
        ).limit(1).correlate(Vehiculo).scalar_subquery()
        estado_sql = case(
            (Pago.id.is_(None), "SIN_MENSUALIDAD"),
            (Pago.inicio > hoy, "PROGRAMADA"),
            (Pago.fin < hoy, "VENCIDA"),
            (Pago.fin <= hoy + timedelta(days=5), "POR_VENCER"),
            else_="VIGENTE",
        )
        consulta = select(Vehiculo, Cliente, Pago, estado_sql).outerjoin(
            Cliente, Cliente.id == Vehiculo.cliente_id
        ).outerjoin(Pago, Pago.id == relevante)
        if placa:
            consulta = consulta.where(Vehiculo.placa == placa.strip().upper())
        if estado:
            consulta = consulta.where(estado_sql == estado)
        total = self.session.scalar(select(func.count()).select_from(consulta.subquery()))
        filas = self.session.execute(consulta.order_by(Vehiculo.placa).offset(offset).limit(limit)).all()
        return MensualidadesPagina(items=[MensualidadRespuesta(
            vehiculo_id=vehiculo.id, placa=vehiculo.placa, tipo=vehiculo.tipo,
            tarifa_mensual=TARIFAS_MENSUALES[vehiculo.tipo],
            cliente_id=vehiculo.cliente_id, cliente_nombre=cliente.nombre if cliente else None,
            telefono=cliente.telefono if cliente else None, pago_id=pago.id if pago else None,
            inicio=pago.inicio if pago else None, fin=pago.fin if pago else None,
            dias_restantes=(pago.fin - hoy).days if pago else None, estado=situacion,
        ) for vehiculo, cliente, pago, situacion in filas], total=total, offset=offset, limit=limit)
