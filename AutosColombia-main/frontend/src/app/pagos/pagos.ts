import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Observable, Subscription, map } from 'rxjs';
import {
  Aviso,
  ConfiguracionAvisos,
  EstadoMensualidad,
  Mensualidad,
  Pagina,
  PagoHistorial,
} from '../models/pago';
import { Operador } from '../models/operador';
import { PagosService } from '../services/pagos.service';
import { EstanciasService } from '../services/estancias.service';
import { AuthService } from '../auth/auth.service';

type Tab = 'mensualidades' | 'historial' | 'avisos';
type Listado =
  | { tipo: 'mensualidades'; pagina: Pagina<Mensualidad> }
  | { tipo: 'historial'; pagina: Pagina<PagoHistorial> }
  | { tipo: 'avisos'; pagina: Pagina<Aviso> };

export function hoyBogota(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Bogota' }).format(new Date());
}

export function siguienteMes(value: string): string {
  const [anio, mes, dia] = value.split('-').map(Number);
  const nuevoAnio = anio + (mes === 12 ? 1 : 0);
  const nuevoMes = (mes % 12) + 1;
  const ultimoDia = new Date(Date.UTC(nuevoAnio, nuevoMes, 0)).getUTCDate();
  return `${nuevoAnio}-${String(nuevoMes).padStart(2, '0')}-${String(Math.min(dia, ultimoDia)).padStart(2, '0')}`;
}

@Component({
  selector: 'app-pagos',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './pagos.html',
  styleUrl: './pagos.css',
})
export class Pagos {
  private readonly auth = inject(AuthService);
  private readonly api = inject(PagosService);
  private readonly catalogos = inject(EstanciasService);
  private readonly fb = inject(FormBuilder);
  private readonly destroy = inject(DestroyRef);
  private listRequest?: Subscription;
  private solicitudId = crypto.randomUUID();
  private consultaRequest?: Subscription;
  readonly tab = signal<Tab>('mensualidades');
  readonly mensualidades = signal<Mensualidad[]>([]);
  readonly historial = signal<PagoHistorial[]>([]);
  readonly avisos = signal<Aviso[]>([]);
  readonly operadores = signal<Operador[]>([]);
  readonly configuracion = signal<ConfiguracionAvisos | null>(null);
  readonly configError = signal('');
  readonly operadoresError = signal('');
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly consultando = signal(false);
  readonly showForm = signal(false);
  readonly seleccionado = signal<Mensualidad | null>(null);
  readonly error = signal('');
  readonly formError = signal('');
  readonly success = signal('');
  readonly total = signal(0);
  readonly offset = signal(0);
  readonly limit = 10;
  readonly page = computed(() => Math.floor(this.offset() / this.limit) + 1);
  readonly pages = computed(() => Math.max(1, Math.ceil(this.total() / this.limit)));
  readonly estados: { valor: EstadoMensualidad; nombre: string }[] = [
    { valor: 'VIGENTE', nombre: 'Vigente' },
    { valor: 'POR_VENCER', nombre: 'Por vencer' },
    { valor: 'VENCIDA', nombre: 'Vencida' },
    { valor: 'PROGRAMADA', nombre: 'Programada' },
    { valor: 'SIN_MENSUALIDAD', nombre: 'Sin mensualidad' },
  ];
  readonly filtro = this.fb.nonNullable.group({ placa: '', estado: '' });
  readonly form = this.fb.group({
    placa: this.fb.nonNullable.control('', Validators.required),
    operador_id: this.fb.control<number | null>(null, Validators.required),
    fecha_pago: this.fb.nonNullable.control(hoyBogota(), Validators.required),
    inicio: this.fb.nonNullable.control(hoyBogota(), Validators.required),
    fin: this.fb.nonNullable.control(siguienteMes(hoyBogota()), Validators.required),
  });

  constructor() {
    this.form.controls.placa.valueChanges.pipe(takeUntilDestroyed(this.destroy)).subscribe(() => {
      this.consultaRequest?.unsubscribe();
      this.consultando.set(false);
      this.seleccionado.set(null);
    });
    this.form.controls.inicio.valueChanges
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe((inicio) => {
        if (/^\d{4}-\d{2}-\d{2}$/.test(inicio))
          this.form.controls.fin.setValue(siguienteMes(inicio));
      });
    this.cargar();
    this.cargarOperadores();
    this.cargarConfiguracion();
  }

  cargarOperadores(): void {
    this.operadoresError.set('');
    this.catalogos
      .operadores()
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (items) => this.operadores.set(items),
        error: () =>
          this.operadoresError.set(
            'No se pudieron cargar los operadores. Actualiza para registrar un pago.',
          ),
      });
  }

  cargarConfiguracion(): void {
    this.configError.set('');
    this.api
      .configuracion()
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (config) => this.configuracion.set(config),
        error: () => this.configError.set('No se pudo comprobar la conexión de WhatsApp Business.'),
      });
  }

  cambiarTab(tab: Tab): void {
    if (this.saving()) return;
    this.tab.set(tab);
    this.cargar();
  }

  cargar(offset = 0): void {
    this.listRequest?.unsubscribe();
    this.loading.set(true);
    this.error.set('');
    const filtro = this.filtro.getRawValue();
    let request: Observable<Listado>;
    switch (this.tab()) {
      case 'mensualidades':
        request = this.api
          .mensualidades(filtro.placa, filtro.estado, offset, this.limit)
          .pipe(map((pagina) => ({ tipo: 'mensualidades' as const, pagina })));
        break;
      case 'historial':
        request = this.api
          .historial(filtro.placa, offset, this.limit)
          .pipe(map((pagina) => ({ tipo: 'historial' as const, pagina })));
        break;
      case 'avisos':
        request = this.api
          .avisos(offset, this.limit)
          .pipe(map((pagina) => ({ tipo: 'avisos' as const, pagina })));
        break;
    }
    this.listRequest = request.pipe(takeUntilDestroyed(this.destroy)).subscribe({
      next: (resultado) => {
        switch (resultado.tipo) {
          case 'mensualidades':
            this.mensualidades.set(resultado.pagina.items);
            break;
          case 'historial':
            this.historial.set(resultado.pagina.items);
            break;
          case 'avisos':
            this.avisos.set(resultado.pagina.items);
            break;
        }
        this.total.set(resultado.pagina.total);
        this.offset.set(offset);
        this.loading.set(false);
      },
      error: (error) => {
        this.loading.set(false);
        this.error.set(this.mensaje(error));
      },
    });
  }

  nuevo(item?: Mensualidad): void {
    if (this.saving()) return;
    this.consultaRequest?.unsubscribe();
    this.solicitudId = crypto.randomUUID();
    this.form.reset({
      placa: item?.placa ?? '',
      operador_id: this.auth.usuario()?.operador_id ?? null,
      fecha_pago: hoyBogota(),
      inicio: hoyBogota(),
      fin: siguienteMes(hoyBogota()),
    });
    this.consultando.set(false);
    this.seleccionado.set(item ?? null);
    this.formError.set('');
    this.success.set('');
    this.showForm.set(true);
    if (item) this.sugerirPeriodo(item);
  }

  private sugerirPeriodo(item: Mensualidad): void {
    let inicio = hoyBogota();
    if (item.fin && item.fin >= inicio) {
      const siguiente = new Date(`${item.fin}T00:00:00Z`);
      siguiente.setUTCDate(siguiente.getUTCDate() + 1);
      inicio = siguiente.toISOString().slice(0, 10);
    }
    this.form.patchValue({ inicio, fin: siguienteMes(inicio) });
  }

  buscarVehiculo(): void {
    if (this.saving() || this.consultando()) return;
    const placa = this.form.controls.placa.value.trim().toUpperCase();
    if (!placa) {
      this.formError.set('Escribe la placa del vehículo.');
      return;
    }
    this.form.controls.placa.setValue(placa);
    this.formError.set('');
    this.consultando.set(true);
    this.consultaRequest = this.api
      .mensualidades(placa)
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (pagina) => {
          this.consultando.set(false);
          const item = pagina.items[0];
          this.seleccionado.set(item ?? null);
          if (item) this.sugerirPeriodo(item);
          else this.formError.set('Vehículo no registrado.');
        },
        error: (error) => {
          this.consultando.set(false);
          this.formError.set(this.mensaje(error));
        },
      });
  }

  guardar(): void {
    if (this.saving() || this.consultando() || this.operadoresError()) return;
    this.form.markAllAsTouched();
    const raw = this.form.getRawValue();
    if (this.form.invalid) {
      this.formError.set('Completa la placa, las fechas y el operador responsable.');
      return;
    }
    if (this.seleccionado()?.placa !== raw.placa.trim().toUpperCase()) {
      this.formError.set('Busca el vehículo antes de registrar su pago.');
      return;
    }
    if (!this.seleccionado()?.cliente_id) {
      this.formError.set('Asocia el vehículo con su cliente responsable desde Vehículos.');
      return;
    }
    if (raw.fin < raw.inicio) {
      this.formError.set('El vencimiento debe ser igual o posterior al inicio.');
      return;
    }
    this.saving.set(true);
    this.formError.set('');
    this.api
      .registrar({
        ...raw,
        placa: raw.placa.trim().toUpperCase(),
        operador_id: raw.operador_id!,
        valor: this.seleccionado()!.tarifa_mensual,
        solicitud_id: this.solicitudId,
      })
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (pago) => {
          this.saving.set(false);
          this.showForm.set(false);
          this.success.set(
            `Pago #${pago.id} registrado por ${this.moneda(pago.valor)}. Periodo del ${this.fecha(pago.inicio)} al ${this.fecha(pago.fin)}, inclusive.`,
          );
          this.tab.set('mensualidades');
          this.cargar();
        },
        error: (error) => {
          this.saving.set(false);
          this.formError.set(this.mensaje(error));
        },
      });
  }

  reintentar(aviso: Aviso): void {
    if (this.saving()) return;
    this.saving.set(true);
    this.api
      .reintentar(aviso.id)
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (data) => {
          this.saving.set(false);
          this.success.set(data.detail);
          this.cargar(this.offset());
        },
        error: (error) => {
          this.saving.set(false);
          this.error.set(this.mensaje(error));
        },
      });
  }

  whatsapp(aviso: Aviso): string {
    return `https://wa.me/${aviso.telefono}?text=${encodeURIComponent(aviso.texto)}`;
  }

  avisoManualDisponible(aviso: Aviso): boolean {
    return (
      !!aviso.telefono &&
      ['PENDIENTE', 'ERROR', 'REVISION'].includes(aviso.estado) &&
      aviso.programado_para <= hoyBogota() &&
      aviso.fin >= hoyBogota()
    );
  }

  nombreEstado(estado: string): string {
    const nombres: Record<string, string> = {
      SIN_MENSUALIDAD: 'Sin mensualidad',
      PROGRAMADA: 'Programada',
      VIGENTE: 'Vigente',
      POR_VENCER: 'Por vencer',
      VENCIDA: 'Vencida',
      PENDIENTE: 'Pendiente',
      EN_PROCESO: 'En proceso',
      ACEPTADO: 'Aceptado por WhatsApp',
      ENTREGADO: 'Entregado',
      LEIDO: 'Leído',
      ERROR: 'Error',
      REVISION: 'Requiere revisión',
      OMITIDO: 'Omitido',
      CANCELADO: 'Cancelado por renovación',
    };
    return nombres[estado] ?? estado;
  }

  fecha(value: string | null): string {
    return value
      ? new Intl.DateTimeFormat('es-CO', { timeZone: 'UTC', dateStyle: 'medium' }).format(
          new Date(`${value}T00:00:00Z`),
        )
      : '—';
  }

  moneda(value: string): string {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      maximumFractionDigits: 2,
    }).format(Number(value));
  }

  private mensaje(error: HttpErrorResponse): string {
    if (typeof error.error?.detail === 'string') return error.error.detail;
    if (error.status === 422) return 'Revisa el valor, las fechas y los datos seleccionados.';
    return 'No se pudo completar la solicitud. Actualiza el listado antes de repetir un pago; podría haberse registrado.';
  }
}
