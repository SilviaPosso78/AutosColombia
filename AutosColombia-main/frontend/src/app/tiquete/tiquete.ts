import { DOCUMENT } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
import { Tiquete as DatosTiquete } from '../models/tiquete';
import { EstanciasService } from '../services/estancias.service';

@Component({
  selector: 'app-tiquete',
  imports: [RouterLink],
  templateUrl: './tiquete.html',
  styleUrl: './tiquete.css',
})
export class Tiquete {
  private readonly api = inject(EstanciasService);
  private readonly destroy = inject(DestroyRef);
  private readonly document = inject(DOCUMENT);
  private request?: Subscription;
  private estanciaId: number | null = null;
  readonly datos = signal<DatosTiquete | null>(null);
  readonly loading = signal(false);
  readonly error = signal('');

  constructor() {
    inject(ActivatedRoute)
      .paramMap.pipe(takeUntilDestroyed(this.destroy))
      .subscribe((params) => {
        this.request?.unsubscribe();
        const id = Number(params.get('id'));
        this.estanciaId = Number.isSafeInteger(id) && id > 0 ? id : null;
        this.cargar();
      });
  }

  cargar(): void {
    this.request?.unsubscribe();
    this.datos.set(null);
    this.error.set('');
    if (this.estanciaId === null) {
      this.loading.set(false);
      this.error.set('El número de tiquete no es válido.');
      return;
    }
    this.loading.set(true);
    this.request = this.api
      .tiquete(this.estanciaId)
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (datos) => {
          this.datos.set(datos);
          this.loading.set(false);
        },
        error: (error) => {
          this.loading.set(false);
          this.error.set(
            error.status === 404
              ? 'Tiquete no encontrado.'
              : 'No se pudo cargar el tiquete. Actualiza para volver a intentarlo.',
          );
        },
      });
  }

  imprimir(): void {
    if (this.datos() && !this.loading()) this.document.defaultView?.print();
  }

  fecha(value: string): string {
    return new Intl.DateTimeFormat('es-CO', {
      timeZone: 'America/Bogota',
      dateStyle: 'long',
      timeStyle: 'medium',
    }).format(new Date(value));
  }
}
