import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Subscription, forkJoin } from 'rxjs';
import { Celda } from '../models/celda';
import { Operador } from '../models/operador';
import { MovimientosPagina } from '../models/tiquete';
import { EstanciasService } from '../services/estancias.service';

@Component({
  selector: 'app-movimientos',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './movimientos.html',
  styleUrl: './movimientos.css',
})
export class Movimientos {
  private readonly api = inject(EstanciasService);
  private readonly fb = inject(FormBuilder);
  private readonly destroy = inject(DestroyRef);
  private request?: Subscription;
  readonly resultado = signal<MovimientosPagina | null>(null);
  readonly loading = signal(false);
  readonly error = signal('');
  readonly catalogError = signal('');
  readonly celdas = signal<Celda[]>([]);
  readonly operadores = signal<Operador[]>([]);
  readonly actualizado = signal('');
  readonly limit = 10;
  readonly page = computed(() => Math.floor((this.resultado()?.offset ?? 0) / this.limit) + 1);
  readonly pages = computed(() =>
    Math.max(1, Math.ceil((this.resultado()?.total ?? 0) / this.limit)),
  );
  readonly filtros = this.fb.group({
    placa: this.fb.nonNullable.control(''),
    desde: this.fb.nonNullable.control(''),
    hasta: this.fb.nonNullable.control(''),
    celda_id: this.fb.control<number | null>(null),
    operador_id: this.fb.control<number | null>(null),
    movimiento: this.fb.nonNullable.control(''),
  });

  constructor() {
    this.cargar();
    this.cargarCatalogos();
  }

  cargarCatalogos(): void {
    this.catalogError.set('');
    forkJoin({ celdas: this.api.celdas(), operadores: this.api.operadores() })
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (data) => {
          this.celdas.set(data.celdas);
          this.operadores.set(data.operadores);
        },
        error: () =>
          this.catalogError.set('No se pudieron cargar los filtros de celda y operador.'),
      });
  }

  cargar(offset = 0): void {
    this.request?.unsubscribe();
    this.error.set('');
    const filtros = this.filtros.getRawValue();
    if (filtros.desde && filtros.hasta && filtros.desde > filtros.hasta) {
      this.loading.set(false);
      this.error.set('La fecha inicial debe ser igual o anterior a la fecha final.');
      return;
    }
    this.loading.set(true);
    this.request = this.api
      .movimientos(filtros, offset, this.limit)
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (data) => {
          this.loading.set(false);
          if (offset > 0 && offset >= data.total) {
            this.cargar();
            return;
          }
          this.resultado.set(data);
          this.actualizado.set(this.fecha(new Date().toISOString()));
        },
        error: (error: HttpErrorResponse) => {
          this.loading.set(false);
          this.error.set(
            typeof error.error?.detail === 'string'
              ? error.error.detail
              : 'No se pudo consultar el historial. Intenta actualizar el reporte.',
          );
        },
      });
  }

  limpiar(): void {
    this.filtros.reset();
    this.cargar();
  }

  fecha(value: string): string {
    return new Intl.DateTimeFormat('es-CO', {
      timeZone: 'America/Bogota',
      dateStyle: 'medium',
      timeStyle: 'medium',
    }).format(new Date(value));
  }
}
