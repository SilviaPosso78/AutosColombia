import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { timer, timeout } from 'rxjs';
import { OcupacionCelda } from '../models/celda';
import { ApiService } from '../services/api.service';
import { EstanciasService } from '../services/estancias.service';

@Component({
  imports: [RouterLink],
  selector: 'app-home',
  styleUrl: './home.css',
  templateUrl: './home.html',
})
export class Home {
  private readonly api = inject(ApiService);
  private readonly estancias = inject(EstanciasService);
  private readonly destroy = inject(DestroyRef);
  readonly celdas = signal<OcupacionCelda[] | null>(null);
  readonly loading = signal(false);
  readonly error = signal('');
  readonly actualizado = signal('');
  readonly connectionState = signal<'checking' | 'available' | 'unavailable'>('checking');
  readonly connectionMessage = computed(() => {
    switch (this.connectionState()) {
      case 'available':
        return 'Servicio disponible';
      case 'unavailable':
        return 'No se pudo conectar con el servicio';
      default:
        return 'Comprobando conexión…';
    }
  });
  readonly resumen = computed(() => {
    const celdas = this.celdas();
    if (celdas === null) return null;
    const ocupadas = celdas.filter((celda) => celda.ocupada);
    const sectores = [
      { nombre: 'Motocicletas', rango: 'Celdas para motos', tipo: 'Motocicletas' },
      {
        nombre: 'Automóviles y camionetas',
        rango: 'Celdas para carros',
        tipo: 'Automóviles y camionetas',
      },
    ].map((sector) => {
      const celdasSector = celdas.filter((celda) => celda.tipo === sector.tipo);
      const ocupadasSector = celdasSector.filter((celda) => celda.ocupada).length;
      return {
        ...sector,
        total: celdasSector.length,
        ocupadas: ocupadasSector,
        libres: celdasSector.length - ocupadasSector,
      };
    });
    return {
      total: celdas.length,
      ocupadas: ocupadas.length,
      libres: celdas.length - ocupadas.length,
      porcentaje: celdas.length ? Math.round((ocupadas.length / celdas.length) * 100) : 0,
      sectores,
      dentro: [...ocupadas]
        .sort((a, b) => (b.entrada ?? '').localeCompare(a.entrada ?? ''))
        .slice(0, 5),
    };
  });

  constructor() {
    this.actualizar();
    timer(10000, 10000)
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe(() => this.cargarResumen());
  }

  actualizar(): void {
    if (this.loading()) return;
    this.connectionState.set('checking');
    this.api
      .health()
      .pipe(timeout(5000), takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (response) =>
          this.connectionState.set(response?.status === 'ok' ? 'available' : 'unavailable'),
        error: () => this.connectionState.set('unavailable'),
      });
    this.cargarResumen();
  }

  private cargarResumen(): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.estancias
      .ocupacion()
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (celdas) => {
          this.celdas.set(celdas);
          this.actualizado.set(this.fecha(new Date().toISOString()));
          this.error.set('');
          this.loading.set(false);
        },
        error: () => {
          this.celdas.set(null);
          this.error.set('No se pudo consultar la ocupación. Intenta actualizar el resumen.');
          this.loading.set(false);
        },
      });
  }

  fecha(value: string): string {
    return new Intl.DateTimeFormat('es-CO', {
      timeZone: 'America/Bogota',
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(value));
  }
}
