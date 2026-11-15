import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from './auth.service';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule],
  templateUrl: './login.html',
  styleUrl: './login.css',
})
export class Login {
  private readonly auth = inject(AuthService);
  readonly passwordActualizada = this.auth.passwordActualizada;
  private readonly router = inject(Router);
  private readonly destroy = inject(DestroyRef);
  readonly loading = signal(false);
  readonly error = signal('');
  readonly showPassword = signal(false);
  readonly capsLock = signal(false);
  readonly form = inject(FormBuilder).nonNullable.group({
    usuario: ['', [Validators.required, Validators.pattern(/^[a-zA-Z0-9_.-]{3,80}$/)]],
    password: ['', [Validators.required, Validators.maxLength(128), Validators.pattern(/\S/)]],
  });

  entrar(): void {
    if (this.loading()) return;
    this.error.set('');
    this.form.controls.usuario.setValue(this.form.controls.usuario.value.trim());
    this.form.markAllAsTouched();
    if (this.form.invalid) return;
    this.loading.set(true);
    const { usuario, password } = this.form.getRawValue();
    this.auth
      .login(usuario, password)
      .pipe(takeUntilDestroyed(this.destroy))
      .subscribe({
        next: () => {
          this.loading.set(false);
          this.showPassword.set(false);
          this.form.controls.password.reset();
          void this.router.navigateByUrl(this.auth.destino());
        },
        error: (error) => {
          this.loading.set(false);
          this.showPassword.set(false);
          this.form.controls.password.reset();
          this.error.set(
            error.status === 401
              ? 'Usuario o contraseña incorrectos. Revisa tus datos e intenta nuevamente.'
              : error.status === 422
                ? 'Revisa el usuario y la contraseña ingresados.'
                : 'No pudimos iniciar sesión. Intenta nuevamente en un momento.',
          );
        },
      });
  }
}
