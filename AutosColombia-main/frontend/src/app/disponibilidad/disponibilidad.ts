import { DOCUMENT } from '@angular/common';
import {
  Component,
  DestroyRef,
  Injector,
  afterNextRender,
  computed,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { OcupacionCelda } from '../models/celda';
import { MovimientosPagina } from '../models/tiquete';
import { EstanciasService } from '../services/estancias.service';

@Component({
  selector: 'app-disponibilidad',
  imports: [RouterLink],
  templateUrl: './disponibilidad.html',
  styleUrl: './disponibilidad.css',
})
export class Disponibilidad {
  private readonly api = inject(EstanciasService);
  private readonly destroy = inject(DestroyRef);
  private readonly injector = inject(Injector);
  private readonly document = inject(DOCUMENT);
  private historyRequest?: Subscription;
  readonly celdas = signal<OcupacionCelda[]>([]);
  readonly loading = signal(false);
  readonly error = signal('');
  readonly actualizado = signal('');
  readonly tipo = signal('');
  readonly estado = signal('');
  readonly ocupadas = computed(() => this.celdas().filter((cell) => cell.ocupada).length);
  readonly libres = computed(() => this.celdas().length - this.ocupadas());
  readonly visibles = computed(() =>
    this.celdas().filter(
      (cell) =>
        (!this.tipo() || cell.tipo === this.tipo()) &&
        (!this.estado() || cell.ocupada === (this.estado() === 'OCUPADA')),
    ),
  );
  readonly sectores = computed(() =>
    ['Motocicletas', 'Automóviles y camionetas']
      .map((nombre) => ({
        nombre,
        celdas: this.visibles().filter((cell) => cell.tipo === nombre),
      }))
      .filter((sector) => sector.celdas.length),
  );
  readonly seleccionada = signal<OcupacionCelda | null>(null);
  readonly historial = signal<MovimientosPagina | null>(null);
  readonly historyLoading = signal(false);
  readonly historyError = signal('');
  readonly historyLimit = 10;

  constructor() {
    this.actualizar();
    interval(10000)
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe(() => this.actualizar());
  }

  actualizar(): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.api
      .ocupacion()
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (data) => {
          this.celdas.set([...data].sort((a, b) => a.codigo.localeCompare(b.codigo)));
          this.actualizado.set(this.fecha(new Date().toISOString()));
          this.loading.set(false);
          this.error.set('');
          const selected = this.seleccionada();
          if (selected)
            this.seleccionada.set(data.find((cell) => cell.id === selected.id) ?? selected);
        },
        error: () => {
          this.loading.set(false);
          this.error.set(
            this.actualizado()
              ? 'No se pudo actualizar. La última disponibilidad consultada puede haber cambiado.'
              : 'No se pudo consultar la disponibilidad. Intenta actualizar nuevamente.',
          );
        },
      });
  }

  verHistorial(celda: OcupacionCelda, offset = 0): void {
    this.historyRequest?.unsubscribe();
    this.seleccionada.set(celda);
    this.historial.set(null);
    this.historyLoading.set(true);
    this.historyError.set('');
    afterNextRender(
      () => {
        const panel = this.document.getElementById('cell-history');
        panel?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
        panel?.focus({ preventScroll: true });
      },
      { injector: this.injector },
    );
    this.historyRequest = this.api
      .movimientos(
        {
          celda_id: celda.id,
          placa: '',
          desde: '',
          hasta: '',
          operador_id: null,
          movimiento: '',
        },
        offset,
        this.historyLimit,
      )
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (data) => {
          this.historyLoading.set(false);
          if (offset > 0 && offset >= data.total) {
            this.verHistorial(celda);
            return;
          }
          this.historial.set(data);
        },
        error: () => {
          this.historyLoading.set(false);
          this.historyError.set('No se pudo consultar el historial. Actualiza para reintentar.');
        },
      });
  }

  cerrarHistorial(): void {
    this.historyRequest?.unsubscribe();
    this.seleccionada.set(null);
    this.historial.set(null);
    this.historyLoading.set(false);
  }

  fecha(value: string): string {
    return new Intl.DateTimeFormat('es-CO', {
      timeZone: 'America/Bogota',
      dateStyle: 'medium',
      timeStyle: 'medium',
    }).format(new Date(value));
  }
}
