import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { EMPTY, Observable, expand, map, reduce, throwError, timeout } from 'rxjs';
import { Celda, OcupacionCelda } from '../models/celda';
import { Operador } from '../models/operador';
import {
  EntradaCrear,
  EntradaRegistrada,
  SalidaCrear,
  Estancia,
  EstadoVehiculo,
} from '../models/estancia';
import { FiltrosMovimientos, MovimientosPagina, Tiquete } from '../models/tiquete';
import { API_BASE_URL } from './api.service';
import { OperadoresService } from './operadores.service';

interface Pagina<T> {
  items: T[];
  offset: number;
  limit: number;
  total: number;
}

@Injectable({ providedIn: 'root' })
export class EstanciasService {
  private readonly http = inject(HttpClient);
  private readonly base = `${inject(API_BASE_URL)}/estancias`;
  private readonly operators = inject(OperadoresService);

  entrada(data: EntradaCrear) {
    return this.http.post<EntradaRegistrada>(`${this.base}/entrada`, data).pipe(timeout(15000));
  }
  ocupacion() {
    return this.http.get<OcupacionCelda[]>(`${this.base}/ocupacion`).pipe(timeout(15000));
  }
  tiquete(estanciaId: number) {
    return this.http.get<Tiquete>(`${this.base}/tiquetes/${estanciaId}`).pipe(timeout(15000));
  }
  movimientos(filtros: FiltrosMovimientos, offset = 0, limit = 10) {
    let params = new HttpParams().set('offset', offset).set('limit', limit);
    for (const [campo, valor] of Object.entries(filtros)) {
      if (valor !== null && valor !== '') {
        params = params.set(campo, campo === 'placa' ? String(valor).trim().toUpperCase() : valor);
      }
    }
    return this.http
      .get<MovimientosPagina>(`${this.base}/movimientos`, { params })
      .pipe(timeout(15000));
  }
  salida(data: SalidaCrear) {
    return this.http.post<Estancia>(`${this.base}/salida`, data).pipe(timeout(15000));
  }
  consultar(placa: string) {
    return this.http
      .get<EstadoVehiculo>(`${this.base}/vehiculo/${encodeURIComponent(placa)}`)
      .pipe(timeout(15000));
  }
  celdas(): Observable<Celda[]> {
    return this.ocupacion().pipe(
      map((items) => items.map(({ id, codigo, tipo }) => ({ id, codigo, tipo }))),
    );
  }
  operadores(): Observable<Operador[]> {
    return this.todas((offset) => this.operators.list(offset, 100));
  }

  private todas<T>(load: (offset: number) => Observable<Pagina<T>>): Observable<T[]> {
    return load(0).pipe(
      expand((page) => {
        const next = page.offset + page.items.length;
        if (next >= page.total) return EMPTY;
        if (!page.items.length)
          return throwError(() => new Error('Catálogo incompleto. Recarga las opciones.'));
        return load(next);
      }),
      reduce((items, page) => [...items, ...page.items], [] as T[]),
    );
  }
}
