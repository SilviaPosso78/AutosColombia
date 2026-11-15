import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { EMPTY, Observable, expand, reduce, throwError, timeout } from 'rxjs';
import { Cliente, ClienteActualizar, ClienteCrear, ClientesPagina } from '../models/cliente';
import { API_BASE_URL } from './api.service';

@Injectable({ providedIn: 'root' })
export class ClientesService {
  private readonly http = inject(HttpClient);
  private readonly base = `${inject(API_BASE_URL)}/clientes`;

  list(offset: number, limit: number) {
    return this.http
      .get<ClientesPagina>(this.base, { params: { offset, limit } })
      .pipe(timeout(15000));
  }
  get(id: number) {
    return this.http.get<Cliente>(`${this.base}/${id}`).pipe(timeout(15000));
  }
  create(data: ClienteCrear) {
    return this.http.post<Cliente>(this.base, data).pipe(timeout(15000));
  }
  update(id: number, data: ClienteActualizar) {
    return this.http.patch<Cliente>(`${this.base}/${id}`, data).pipe(timeout(15000));
  }
  delete(id: number) {
    return this.http.delete<void>(`${this.base}/${id}`).pipe(timeout(15000));
  }
  all(): Observable<Cliente[]> {
    return this.list(0, 100).pipe(
      expand((page) => {
        const next = page.offset + page.items.length;
        if (next >= page.total) return EMPTY;
        if (!page.items.length)
          return throwError(() => new Error('Catálogo incompleto. Recarga las opciones.'));
        return this.list(next, 100);
      }),
      reduce((items, page) => [...items, ...page.items], [] as Cliente[]),
    );
  }
}
