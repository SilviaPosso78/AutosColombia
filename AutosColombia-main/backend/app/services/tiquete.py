from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import func, literal, select, true, union_all
from sqlalchemy.orm import Session

from app.models import Estancia, Tiquete
from app.schemas.tiquete import MovimientoRespuesta, MovimientosPagina, TiqueteRespuesta
from app.services.estancia import EstanciaError, respuesta_tiquete, transaccion


class ServicioTiquete:
    def __init__(self, session: Session) -> None:
        self.session = session

    @transaccion
    def consultar(self, estancia_id: int) -> TiqueteRespuesta:
        fila = self.session.execute(select(Estancia, Tiquete).join(
            Tiquete, Tiquete.estancia_id == Estancia.id
        ).where(Estancia.id == estancia_id)).one_or_none()
        if fila is None:
            raise EstanciaError(404, "Tiquete no encontrado.")
        return respuesta_tiquete(*fila)

    @transaccion
    def movimientos(
        self, placa: str | None, desde: date | None, hasta: date | None,
        celda_id: int | None, operador_id: int | None, movimiento: str | None,
        offset: int, limit: int,
    ) -> MovimientosPagina:
        if desde and hasta and desde > hasta:
            raise EstanciaError(422, "La fecha inicial debe ser igual o anterior a la fecha final.")
        entradas = select(
            Estancia.id.label("estancia_id"), Tiquete.placa, Tiquete.tipo_vehiculo,
            literal("ENTRADA").label("movimiento"), Estancia.entrada.label("fecha"),
            Estancia.celda_id, Tiquete.celda_codigo, Tiquete.puerta,
            Estancia.operador_entrada_id.label("operador_id"),
            Tiquete.operador_entrada_nombre.label("operador_nombre"),
        ).join(Tiquete, Tiquete.estancia_id == Estancia.id)
        salidas = select(
            Estancia.id.label("estancia_id"), Tiquete.placa, Tiquete.tipo_vehiculo,
            literal("SALIDA").label("movimiento"), Estancia.salida.label("fecha"),
            Estancia.celda_id, Tiquete.celda_codigo, literal("Salida").label("puerta"),
            Estancia.operador_salida_id.label("operador_id"),
            Tiquete.operador_salida_nombre.label("operador_nombre"),
        ).join(Tiquete, Tiquete.estancia_id == Estancia.id).where(Estancia.salida.is_not(None))
        movimientos = union_all(entradas, salidas).subquery()
        consulta = select(movimientos)
        if placa and placa.strip():
            consulta = consulta.where(movimientos.c.placa == placa.strip().upper())
        zona = ZoneInfo("America/Bogota")
        if desde:
            consulta = consulta.where(movimientos.c.fecha >= datetime.combine(desde, time.min, zona))
        if hasta:
            consulta = consulta.where(movimientos.c.fecha <= datetime.combine(hasta, time.max, zona))
        if celda_id is not None:
            consulta = consulta.where(movimientos.c.celda_id == celda_id)
        if operador_id is not None:
            consulta = consulta.where(movimientos.c.operador_id == operador_id)
        if movimiento:
            consulta = consulta.where(movimientos.c.movimiento == movimiento)
        filtrados = consulta.cte("movimientos_filtrados")
        resumen = select(
            func.count().label("total"),
            func.count().filter(filtrados.c.movimiento == "ENTRADA").label("entradas"),
            func.count().filter(filtrados.c.movimiento == "SALIDA").label("salidas"),
        ).select_from(filtrados).subquery()
        pagina = select(filtrados).order_by(
            filtrados.c.fecha.desc(), filtrados.c.estancia_id.desc(), filtrados.c.movimiento.desc()
        ).offset(offset).limit(limit).subquery()
        # Una consulta conserva el mismo estado de datos para totales y página, incluso si está vacía.
        filas = self.session.execute(select(resumen, pagina).select_from(
            resumen.outerjoin(pagina, true())
        ).order_by(pagina.c.fecha.desc(), pagina.c.estancia_id.desc(), pagina.c.movimiento.desc())).mappings().all()
        items = []
        for fila in filas:
            if fila["estancia_id"] is not None:
                items.append(MovimientoRespuesta(
                    **{campo: fila[campo] for campo in pagina.c.keys()},
                    tiquete_numero=f"AC-{fila['estancia_id']:08d}",
                ))
        return MovimientosPagina(
            items=items, total=filas[0]["total"], entradas=filas[0]["entradas"],
            salidas=filas[0]["salidas"], offset=offset, limit=limit,
        )
