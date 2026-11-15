"""Crea las cuentas iniciales una sola vez y guarda el acceso en un archivo privado."""
import secrets
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.database import get_engine
from app.models import Operador, Usuario
from app.services.auth import hash_password


def main() -> None:
    destino = Path(__file__).resolve().parent / "tmp" / "acceso_inicial.txt"
    destino.parent.mkdir(exist_ok=True)
    # Escritura exclusiva: nunca reemplaza accesos previos ni cambia contraseñas existentes.
    with destino.open("x", encoding="utf-8") as archivo:
        try:
            with Session(get_engine()) as session, session.begin():
                session.execute(text("LOCK TABLE usuario IN EXCLUSIVE MODE"))
                if session.scalar(select(func.count()).select_from(Usuario)):
                    raise ValueError("Ya existen usuarios. Usa Crear usuarios desde una cuenta administradora.")
                for nombre, rol in (("admin_prueba", "ADMINISTRADOR"), ("operador_prueba", "OPERADOR")):
                    password = secrets.token_urlsafe(18)
                    perfil_id = None
                    if rol == "OPERADOR":
                        perfil = Operador(nombre="Operador de pruebas", telefono="0000000000")
                        session.add(perfil)
                        session.flush()
                        perfil_id = perfil.id
                    session.add(Usuario(usuario=nombre, nombre=nombre.replace("_", " ").title(),
                                        rol=rol, password_hash=hash_password(password), operador_id=perfil_id))
                    archivo.write(f"Usuario {nombre}\nRol {rol}\nContraseña {password}\n\n")
                archivo.flush()
        except Exception:
            archivo.close()
            destino.unlink(missing_ok=True)
            raise
    print("Cuentas iniciales creadas. Consulta backend/tmp/acceso_inicial.txt en tu equipo.")


if __name__ == "__main__":
    main()
