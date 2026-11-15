import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { timeout } from 'rxjs';
import {
  Aviso,
  ConfiguracionAvisos,
  Mensualidad,
  Pagina,
  Pago,
  PagoCrear,
  PagoHistorial,
} from '../models/pago';
import { API_BASE_URL } from './api.service';

@Injectable({ providedIn: 'root' })
export class PagosService {
  private readonly http = inject(HttpClient);
  private readonly base = inject(API_BASE_URL);

  registrar(data: PagoCrear) {
    return this.http.post<Pago>(`${this.base}/pagos`, data).pipe(timeout(15000));
  }

  mensualidades(placa = '', estado = '', offset = 0, limit = 10) {
    let params = new HttpParams().set('offset', offset).set('limit', limit);
    if (placa.trim()) params = params.set('placa', placa.trim().toUpperCase());
    if (estado) params = params.set('estado', estado);
    return this.http
      .get<Pagina<Mensualidad>>(`${this.base}/mensualidades`, { params })
      .pipe(timeout(15000));
  }

  historial(placa = '', offset = 0, limit = 10) {
    let params = new HttpParams().set('offset', offset).set('limit', limit);
    if (placa.trim()) params = params.set('placa', placa.trim().toUpperCase());
    return this.http
      .get<Pagina<PagoHistorial>>(`${this.base}/pagos`, { params })
      .pipe(timeout(15000));
  }

  avisos(offset = 0, limit = 10) {
    return this.http
      .get<Pagina<Aviso>>(`${this.base}/notificaciones`, { params: { offset, limit } })
      .pipe(timeout(15000));
  }

  configuracion() {
    return this.http
      .get<ConfiguracionAvisos>(`${this.base}/notificaciones/configuracion`)
      .pipe(timeout(15000));
  }

  reintentar(avisoId: number) {
    return this.http
      .post<{ detail: string }>(`${this.base}/notificaciones/${avisoId}/reintentar`, {})
      .pipe(timeout(15000));
  }
}
