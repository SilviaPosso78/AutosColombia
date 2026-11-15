import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, ValidatorFn, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from './auth.service';

const passwordsMatch: ValidatorFn = (form) =>
  form.get('password_nueva')?.value === form.get('confirmar')?.value
    ? null
    : { passwordsMismatch: true };

@Component({
  selector: 'app-password',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './password.html',
  styles: [
    `
      .password-management {
        max-width: 660px;
        margin: 0 auto;
        grid-template-columns: 1fr;
      }
      .password-management .field {
        margin: 20px 0;
      }
      .password-management input {
        min-height: 46px;
      }
      .password-management .visibility {
        display: flex;
        gap: 8px;
        align-items: center;
        margin: 20px 0;
      }
      .password-management .visibility input {
        width: 16px;
        min-height: 16px;
        padding: 0;
      }
    `,
  ],
})
export class Password {
  readonly auth = inject(AuthService);
  private readonly destroy = inject(DestroyRef);
  readonly saving = signal(false);
  readonly showPassword = signal(false);
  readonly error = signal('');
  readonly form = inject(FormBuilder).nonNullable.group(
    {
      password_actual: [
        '',
        [Validators.required, Validators.maxLength(128), Validators.pattern(/\S/)],
      ],
      password_nueva: [
        '',
        [
          Validators.required,
          Validators.minLength(8),
          Validators.maxLength(128),
          Validators.pattern(/\S/),
        ],
      ],
      confirmar: ['', Validators.required],
    },
    { validators: passwordsMatch },
  );

  guardar(): void {
    if (this.saving()) return;
    this.form.markAllAsTouched();
    this.error.set('');
    if (this.form.invalid) return;
    const { password_actual, password_nueva } = this.form.getRawValue();
    this.saving.set(true);
    this.auth
      .cambiarPassword(password_actual, password_nueva)
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: () => {
          this.form.reset();
          this.showPassword.set(false);
          this.saving.set(false);
        },
        error: (error) => {
          this.saving.set(false);
          this.form.reset();
          this.showPassword.set(false);
          if (error.status === 401) {
            this.auth.sesionTerminada();
            return;
          }
          this.error.set(
            typeof error.error?.detail === 'string'
              ? error.error.detail
              : 'No se pudo confirmar el cambio. Intenta ingresar con la nueva contraseña antes de repetir la operación.',
          );
        },
      });
  }
}
