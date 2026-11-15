import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs';
import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = (route) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth.restaurar().pipe(
    map((user) => {
      if (!user) return router.parseUrl('/login');
      if (route.data['rol'] && user.rol !== route.data['rol']) {
        return router.parseUrl(auth.destino());
      }
      return true;
    }),
  );
};

export const loginGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth.restaurar().pipe(map((user) => (user ? router.parseUrl(auth.destino()) : true)));
};
