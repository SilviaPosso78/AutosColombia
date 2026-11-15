import { Component, inject, signal } from '@angular/core';
import { AuthService } from './auth/auth.service';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  readonly auth = inject(AuthService);
  readonly closing = signal(false);
  readonly logoutError = signal('');

  logout(): void {
    if (this.closing()) return;
    this.closing.set(true);
    this.logoutError.set('');
    this.auth.logout().subscribe({
      next: () => this.closing.set(false),
      error: () => {
        this.closing.set(false);
        this.logoutError.set('No se pudo cerrar la sesión. Intenta nuevamente.');
      },
    });
  }
}
