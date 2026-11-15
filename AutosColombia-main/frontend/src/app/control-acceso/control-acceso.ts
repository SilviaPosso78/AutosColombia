import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, ValidatorFn, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { forkJoin, Subscription, timer } from 'rxjs';
import { Celda, OcupacionCelda } from '../models/celda';
import { Operador } from '../models/operador';
import { EstadoVehiculo } from '../models/estancia';
import { Tiquete } from '../models/tiquete';
import { EstanciasService } from '../services/estancias.service';
import { AuthService } from '../auth/auth.service';

const nonBlank: ValidatorFn = (c) =>
  typeof c.value === 'string' && c.value.trim() ? null : { required: true };
const placa = (value: string) => value.trim().toUpperCase();

@Component({
  selector: 'app-control-acceso',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './control-acceso.html',
  styleUrl: './control-acceso.css',
})
export class ControlAcceso {
  private readonly api = inject(EstanciasService);
  readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly destroy = inject(DestroyRef);
  private version = 0;
  private ocupacionRequest?: Subscription;
  readonly ocupacion = signal<OcupacionCelda[]>([]);
  readonly ocupacionError = signal('');
  readonly ocupacionLoading = signal(false);
  readonly ultimaActualizacion = signal('');
  readonly libres = computed(() => this.ocupacion().filter((c) => !c.ocupada));
  readonly ocupadas = computed(() => this.ocupacion().filter((c) => c.ocupada));
  readonly sectores = computed(() =>
    [
      { id: 'motos', titulo: 'Motocicletas', tipo: 'Motocicletas' },
      { id: 'carros', titulo: 'Automóviles y camionetas', tipo: 'Automóviles y camionetas' },
    ].map((sector) => {
      const celdas = this.ocupacion().filter((celda) => celda.tipo === sector.tipo);
      const libres = celdas.filter((celda) => !celda.ocupada).length;
      return { ...sector, celdas, libres, ocupadas: celdas.length - libres };
    }),
  );
  readonly entrada = this.fb.group({
    placa: this.fb.nonNullable.control('', nonBlank),
    celda_id: this.fb.control<number | null>(null, Validators.required),
    operador_id: this.fb.control<number | null>(null, Validators.required),
  });
  readonly consulta = this.fb.group({
    placa: this.fb.nonNullable.control('', nonBlank),
    operador_id: this.fb.control<number | null>(null, Validators.required),
  });
  readonly celdas = signal<Celda[]>([]);
  readonly operadores = signal<Operador[]>([]);
  readonly catalogLoading = signal(false);
  readonly catalogError = signal('');
  readonly saving = signal(false);
  readonly querying = signal(false);
  readonly busy = computed(() => this.saving() || this.querying());
  readonly estado = signal<EstadoVehiculo | null>(null);
  readonly errorEntrada = signal('');
  readonly errorConsulta = signal('');
  readonly exitoEntrada = signal('');
  readonly exitoSalida = signal('');
  readonly ultimoTiquete = signal<Tiquete | null>(null);

  constructor() {
    this.consulta.controls.placa.valueChanges
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe(() => {
        this.version++;
        this.estado.set(null);
        this.consulta.controls.operador_id.reset();
        this.errorConsulta.set('');
        this.exitoSalida.set('');
      });
    this.cargarCatalogos();
    this.actualizarOcupacion();
    timer(10000, 10000)
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe(() => {
        if (!this.saving() && !this.ocupacionLoading()) this.actualizarOcupacion();
      });
  }

  seleccionarCelda(id: number): void {
    if (
      this.busy() ||
      this.catalogLoading() ||
      this.catalogError() ||
      this.ocupacionLoading() ||
      this.ocupacionError()
    )
      return;
    if (!this.libres().some((celda) => celda.id === id)) return;
    this.entrada.controls.celda_id.setValue(id);
    this.entrada.controls.celda_id.markAsTouched();
  }

  actualizarOcupacion(): void {
    this.ocupacionRequest?.unsubscribe();
    this.ocupacionLoading.set(true);
    this.ocupacionRequest = this.api
      .ocupacion()
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (celdas) => {
          this.ocupacion.set(celdas);
          this.ocupacionError.set('');
          this.ocupacionLoading.set(false);
          this.ultimaActualizacion.set(this.fecha(new Date().toISOString()));
          const selected = this.entrada.controls.celda_id.value;
          if (!celdas.some((c) => c.id === selected && !c.ocupada)) {
            this.entrada.controls.celda_id.reset();
          }
        },
        error: () => {
          this.ocupacionLoading.set(false);
          this.ocupacionError.set(
            'No se pudo verificar la ocupación. Actualiza para consultar la disponibilidad.',
          );
        },
      });
  }

  cargarCatalogos(): void {
    if (this.catalogLoading() || this.saving()) return;
    this.catalogLoading.set(true);
    this.catalogError.set('');
    this.entrada.controls.celda_id.reset();
    this.entrada.controls.operador_id.reset();
    this.consulta.controls.operador_id.reset();
    forkJoin({ celdas: this.api.celdas(), operadores: this.api.operadores() })
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (data) => {
          this.celdas.set(data.celdas);
          this.operadores.set(data.operadores);
          this.entrada.controls.operador_id.setValue(this.auth.usuario()?.operador_id ?? null);
          this.completarOperadorSalida();
          this.catalogLoading.set(false);
        },
        error: () => {
          this.catalogLoading.set(false);
          this.celdas.set([]);
          this.operadores.set([]);
          this.catalogError.set(
            'No se pudieron cargar todas las opciones. Reintenta actualizar catálogos.',
          );
        },
      });
  }

  registrarEntrada(): void {
    if (this.busy() || this.catalogLoading() || this.catalogError()) return;
    this.entrada.markAllAsTouched();
    if (this.entrada.invalid || this.ocupacionError() || this.ocupacionLoading()) return;
    if (!this.libres().some((c) => c.id === this.entrada.controls.celda_id.value)) {
      this.errorEntrada.set('Selecciona una celda libre.');
      this.actualizarOcupacion();
      return;
    }
    const raw = this.entrada.getRawValue();
    const data = {
      placa: placa(raw.placa),
      celda_id: raw.celda_id!,
      operador_id: raw.operador_id!,
    };
    const codigo =
      this.celdas().find((c) => c.id === data.celda_id)?.codigo ?? String(data.celda_id);
    this.entrada.controls.placa.setValue(data.placa);
    this.saving.set(true);
    this.errorEntrada.set('');
    this.exitoEntrada.set('');
    this.ultimoTiquete.set(null);
    this.version++;
    this.estado.set(null);
    this.api
      .entrada(data)
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (result) => {
          this.saving.set(false);
          this.actualizarOcupacion();
          this.ultimoTiquete.set(result.tiquete ?? null);
          this.exitoEntrada.set(
            `Entrada registrada: ${data.placa}, celda ${codigo}, ${this.fecha(result.entrada)}.`,
          );
        },
        error: (error) => {
          this.saving.set(false);
          this.actualizarOcupacion();
          this.errorEntrada.set(this.mensaje(error));
        },
      });
  }

  buscar(): void {
    if (this.busy()) return;
    this.consulta.controls.placa.markAsTouched();
    if (this.consulta.controls.placa.invalid) return;
    const value = placa(this.consulta.controls.placa.value);
    this.consulta.controls.placa.setValue(value, { emitEvent: false });
    const version = ++this.version;
    this.estado.set(null);
    this.consulta.controls.operador_id.reset();
    this.errorConsulta.set('');
    this.querying.set(true);
    this.api
      .consultar(value)
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (result) => {
          this.querying.set(false);
          if (version !== this.version) return;
          this.estado.set(result);
          this.completarOperadorSalida();
        },
        error: (error) => {
          this.querying.set(false);
          if (version === this.version)
            this.errorConsulta.set(
              error.status === 404 ? 'Vehículo no registrado.' : this.mensaje(error),
            );
        },
      });
  }

  private completarOperadorSalida(): void {
    const operadorId = this.auth.usuario()?.operador_id;
    const operador = this.operadores().find((item) => item.id === operadorId);
    this.consulta.controls.operador_id.setValue(operador?.id ?? null);
  }

  registrarSalida(): void {
    if (this.busy() || this.catalogLoading() || this.catalogError()) return;
    this.consulta.markAllAsTouched();
    const state = this.estado();
    const value = placa(this.consulta.controls.placa.value);
    if (
      this.consulta.invalid ||
      !state?.estancia ||
      !state.esta_dentro ||
      state.vehiculo.placa !== value
    )
      return;
    const version = this.version;
    this.saving.set(true);
    this.errorConsulta.set('');
    this.exitoSalida.set('');
    this.api
      .salida({ placa: value, operador_id: this.consulta.controls.operador_id.value! })
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (result) => {
          this.saving.set(false);
          this.actualizarOcupacion();
          this.estado.set(null);
          if (version !== this.version) return;
          this.exitoSalida.set(
            `Salida registrada: ${value}, celda ${state.estancia!.celda.codigo}, ${this.fecha(result.salida!)}.`,
          );
          this.buscar();
        },
        error: (error) => {
          this.saving.set(false);
          this.actualizarOcupacion();
          this.estado.set(null);
          if (version === this.version)
            this.errorConsulta.set(
              this.mensaje(error) + ' Consulta nuevamente antes de confirmar otra salida.',
            );
        },
      });
  }

  fecha(value: string): string {
    return (
      new Intl.DateTimeFormat('es-CO', {
        timeZone: 'America/Bogota',
        dateStyle: 'medium',
        timeStyle: 'medium',
      }).format(new Date(value)) + ' (Bogotá)'
    );
  }

  private mensaje(error: HttpErrorResponse): string {
    if ([404, 409].includes(error.status) && typeof error.error?.detail === 'string')
      return error.error.detail;
    if (error.status === 422)
      return 'Datos inválidos. Revisa la placa y selecciona una celda y un operador válidos según la operación.';
    return 'No se pudo conectar con el servicio. Consulta el vehículo antes de reintentar: la operación podría haberse completado.';
  }
}
