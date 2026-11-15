import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Celda } from '../models/celda';
import { CeldasService } from '../services/celdas.service';

@Component({
  selector: 'app-celdas',
  imports: [ReactiveFormsModule],
  templateUrl: './celdas.html',
  styleUrl: './celdas.css',
})
export class Celdas {
  private readonly api = inject(CeldasService);
  private readonly destroy = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);
  readonly items = signal<Celda[]>([]);
  readonly total = signal(0);
  readonly offset = signal(0);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly showForm = signal(false);
  readonly editing = signal<number | null>(null);
  readonly error = signal('');
  readonly formError = signal('');
  readonly success = signal('');
  readonly limit = 10;
  readonly page = computed(() => Math.floor(this.offset() / this.limit) + 1);
  readonly pages = computed(() => Math.max(1, Math.ceil(this.total() / this.limit)));
  readonly filtro = this.fb.nonNullable.group({ codigo: '' });
  readonly form = this.fb.nonNullable.group({
    codigo: ['', [Validators.required, Validators.pattern(/\S/), Validators.maxLength(80)]],
    tipo: ['', Validators.required],
  });

  constructor() {
    this.load();
  }

  load(offset = 0): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.error.set('');
    this.api
      .list(offset, this.limit, this.filtro.controls.codigo.value)
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (data) => {
          this.loading.set(false);
          if (offset > 0 && offset >= data.total) {
            this.load();
            return;
          }
          this.items.set(data.items);
          this.total.set(data.total);
          this.offset.set(offset);
        },
        error: () => {
          this.loading.set(false);
          this.error.set('No se pudo consultar el catálogo. Actualiza el listado para reintentar.');
        },
      });
  }

  nuevo(): void {
    this.editing.set(null);
    this.form.reset();
    this.formError.set('');
    this.showForm.set(true);
  }

  editar(celda: Celda): void {
    if (this.saving()) return;
    this.editing.set(celda.id);
    this.form.reset({ codigo: celda.codigo, tipo: celda.tipo });
    this.formError.set('');
    this.showForm.set(true);
  }

  guardar(): void {
    if (this.saving()) return;
    this.form.markAllAsTouched();
    if (this.form.invalid) {
      this.formError.set('Completa el código y selecciona un tipo válido.');
      return;
    }
    const data = this.form.getRawValue();
    data.codigo = data.codigo.trim().toUpperCase();
    this.saving.set(true);
    this.formError.set('');
    this.success.set('');
    const request =
      this.editing() === null ? this.api.create(data) : this.api.update(this.editing()!, data);
    request.pipe(takeUntilDestroyed(this.destroy)).subscribe({
      next: (celda) => {
        this.saving.set(false);
        this.showForm.set(false);
        this.success.set(`Celda ${celda.codigo} guardada.`);
        this.load();
      },
      error: (error) => {
        this.saving.set(false);
        this.formError.set(
          typeof error.error?.detail === 'string'
            ? error.error.detail
            : 'No se pudo guardar. Actualiza el catálogo antes de reintentar.',
        );
      },
    });
  }

  eliminar(celda: Celda): void {
    if (this.saving() || !confirm(`¿Eliminar la celda ${celda.codigo}?`)) return;
    this.saving.set(true);
    this.error.set('');
    this.success.set('');
    this.api
      .delete(celda.id)
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.success.set(`Celda ${celda.codigo} eliminada.`);
          this.load(this.offset());
        },
        error: (error) => {
          this.saving.set(false);
          this.error.set(
            typeof error.error?.detail === 'string'
              ? error.error.detail
              : 'No se pudo eliminar la celda. Actualiza antes de reintentar.',
          );
        },
      });
  }
}
