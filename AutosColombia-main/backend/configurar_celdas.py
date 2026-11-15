"""Configura explícitamente el catálogo fijo, sin cambiar el esquema de la base."""

import sys

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.catalogo_celdas import configurar_catalogo
from app.config import ConfigurationError
from app.database import get_engine


def main() -> int:
    try:
        with Session(get_engine()) as session:
            configurar_catalogo(session)
    except (ConfigurationError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except (SQLAlchemyError, OSError):
        print("No se pudo configurar el catálogo. Revisa la conexión a PostgreSQL.", file=sys.stderr)
        return 1
    print("Catálogo configurado: 70 celdas C01–C70 y 10 celdas M01–M10.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
