import { HttpClient } from '@angular/common/http';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, ValidatorFn, Validators } from '@angular/forms';
import { timeout } from 'rxjs';
import { Usuario } from '../auth/auth.service';
import { API_BASE_URL } from '../services/api.service';
import { EstanciasService } from '../services/estancias.service';
import { Operador } from '../models/operador';

const passwordsMatch: ValidatorFn = (form) =>
  form.get('password')?.value === form.get('confirmPassword')?.value
    ? null
    : { passwordsMismatch: true };

@Component({
  selector: 'app-usuarios',
  imports: [ReactiveFormsModule],
  templateUrl: './usuarios.html',
  styleUrl: './usuarios.css',
})
export class Usuarios {
  private readonly http = inject(HttpClient);
  private readonly base = `${inject(API_BASE_URL)}/usuarios`;
  private readonly destroy = inject(DestroyRef);
  private readonly catalogos = inject(EstanciasService);
  readonly operadores = signal<Operador[]>([]);
  readonly perfilesError = signal('');
  readonly perfilesLoading = signal(false);
  readonly listError = signal('');
  readonly showPassword = signal(false);
  readonly items = signal<Usuario[]>([]);
  readonly total = signal(0);
  readonly offset = signal(0);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly error = signal('');
  readonly success = signal('');
  readonly form = inject(FormBuilder).nonNullable.group(
    {
      usuario: ['', [Validators.required, Validators.pattern(/^[a-zA-Z0-9_.-]{3,80}$/)]],
      password: [
        '',
        [
          Validators.required,
          Validators.minLength(8),
          Validators.maxLength(128),
          Validators.pattern(/\S/),
        ],
      ],
      confirmPassword: ['', Validators.required],
      nombre: ['', [Validators.required, Validators.pattern(/\S/), Validators.maxLength(200)]],
      rol: ['OPERADOR', Validators.required],
      telefono: ['', Validators.maxLength(200)],
      operador_id: [''],
    },
    { validators: passwordsMatch },
  );

  constructor() {
    this.cargar();
    this.cargarPerfiles();
    this.ajustarTelefono();
    this.form.controls.rol.valueChanges
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe(() => this.ajustarTelefono());
    this.form.controls.operador_id.valueChanges
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe(() => this.ajustarTelefono());
  }

  private ajustarTelefono(): void {
    const telefono = this.form.controls.telefono;
    const nuevoPerfil =
      this.form.controls.rol.value === 'OPERADOR' && !this.form.controls.operador_id.value;
    telefono.setValidators(
      nuevoPerfil
        ? [Validators.required, Validators.pattern(/\S/), Validators.maxLength(200)]
        : [Validators.maxLength(200)],
    );
    telefono.updateValueAndValidity({ emitEvent: false });
  }

  cargarPerfiles(): void {
    if (this.perfilesLoading()) return;
    this.perfilesLoading.set(true);
    this.perfilesError.set('');
    this.catalogos
      .operadores()
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (items) => {
          this.operadores.set(items);
          this.perfilesLoading.set(false);
        },
        error: () => {
          this.perfilesLoading.set(false);
          this.perfilesError.set('No se pudieron consultar los empleados existentes.');
        },
      });
  }

  cargar(offset = 0): void {
    if (this.loading()) return;
    this.loading.set(true);
    this.listError.set('');
    this.http
      .get<{ items: Usuario[]; total: number }>(this.base, { params: { offset, limit: 10 } })
      .pipe(timeout(15000), takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (data) => {
          this.items.set(data.items);
          this.total.set(data.total);
          this.offset.set(offset);
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
          this.listError.set(
            'No se pudieron consultar los usuarios. Actualiza el listado para reintentar.',
          );
        },
      });
  }

  guardar(): void {
    if (this.saving()) return;
    this.form.controls.usuario.setValue(this.form.controls.usuario.value.trim());
    this.form.controls.nombre.setValue(this.form.controls.nombre.value.trim());
    this.form.markAllAsTouched();
    this.error.set('');
    this.success.set('');
    const data = this.form.getRawValue();
    if (this.form.invalid) {
      this.error.set(
        this.form.hasError('passwordsMismatch')
          ? 'Las contraseñas deben coincidir.'
          : 'Revisa los campos marcados antes de crear la cuenta.',
      );
      return;
    }
    if (data.rol === 'OPERADOR' && !data.telefono.trim() && !data.operador_id) {
      this.error.set(
        'Completa el teléfono del operador o el identificador de un perfil existente.',
      );
      return;
    }
    const perfilId = data.rol === 'OPERADOR' && data.operador_id ? Number(data.operador_id) : null;
    if (perfilId !== null && (!Number.isSafeInteger(perfilId) || perfilId < 1)) {
      this.error.set('El perfil existente debe tener un identificador válido.');
      return;
    }
    this.saving.set(true);
    this.http
      .post<Usuario>(this.base, {
        usuario: data.usuario,
        nombre: data.nombre,
        password: data.password,
        rol: data.rol,
        telefono: data.rol === 'OPERADOR' ? data.telefono.trim() || null : null,
        operador_id: perfilId,
      })
      .pipe(timeout(15000), takeUntilDestroyed(this.destroy))
      .subscribe({
        next: (user) => {
          this.saving.set(false);
          this.success.set(`Cuenta ${user.usuario} creada.`);
          this.form.reset({ rol: 'OPERADOR' });
          this.showPassword.set(false);
          this.cargar();
          this.cargarPerfiles();
        },
        error: (error) => {
          this.saving.set(false);
          this.form.controls.password.reset();
          this.form.controls.confirmPassword.reset();
          this.showPassword.set(false);
          this.error.set(
            typeof error.error?.detail === 'string'
              ? error.error.detail
              : 'No se pudo crear la cuenta. Revisa los datos antes de reintentar.',
          );
        },
      });
  }

  revocar(user: Usuario): void {
    if (this.saving() || !confirm(`¿Revocar todas las sesiones de ${user.usuario}?`)) return;
    this.saving.set(true);
    this.error.set('');
    this.http
      .post<void>(`${this.base}/${user.id}/revocar-sesiones`, {})
      .pipe(timeout(15000), takeUntilDestroyed(this.destroy))
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.success.set(`Sesiones de ${user.usuario} revocadas.`);
        },
        error: () => {
          this.saving.set(false);
          this.error.set('No se pudieron revocar las sesiones.');
        },
      });
  }
}
