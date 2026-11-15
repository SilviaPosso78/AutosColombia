import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, catchError, finalize, of, shareReplay, tap, timeout } from 'rxjs';
import { API_BASE_URL } from '../services/api.service';

export type Rol = 'ADMINISTRADOR' | 'OPERADOR';
export interface Usuario {
  id: number;
  usuario: string;
  nombre: string;
  rol: Rol;
  activo: boolean;
  operador_id: number | null;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly base = inject(API_BASE_URL);
  private restoration?: Observable<Usuario | null>;
  readonly usuario = signal<Usuario | null>(null);
  readonly passwordActualizada = signal(false);

  restaurar(): Observable<Usuario | null> {
    if (this.usuario()) return of(this.usuario());
    if (!this.restoration) {
      this.restoration = this.http.get<Usuario>(`${this.base}/auth/me`).pipe(
        timeout(15000),
        tap((user) => this.usuario.set(user)),
        catchError(() => of(null)),
        finalize(() => (this.restoration = undefined)),
        shareReplay({ bufferSize: 1, refCount: true }),
      );
    }
    return this.restoration;
  }

  login(usuario: string, password: string) {
    return this.http.post<Usuario>(`${this.base}/auth/login`, { usuario, password }).pipe(
      timeout(15000),
      tap((user) => {
        this.usuario.set(user);
        this.passwordActualizada.set(false);
      }),
    );
  }

  logout() {
    return this.http.post<void>(`${this.base}/auth/logout`, {}).pipe(
      timeout(15000),
      tap(() => this.sesionTerminada()),
    );
  }

  cambiarPassword(password_actual: string, password_nueva: string) {
    return this.http
      .post<void>(`${this.base}/auth/password`, { password_actual, password_nueva })
      .pipe(
        timeout(15000),
        tap(() => {
          this.passwordActualizada.set(true);
          this.sesionTerminada();
        }),
      );
  }

  destino(): string {
    return this.usuario()?.rol === 'ADMINISTRADOR' ? '/gestion/celdas' : '/';
  }

  sesionTerminada(): void {
    this.usuario.set(null);
    void this.router.navigateByUrl('/login');
  }
}
