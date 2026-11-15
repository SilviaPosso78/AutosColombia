from datetime import datetime, timedelta, timezone
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Sesion, Usuario
from app.schemas.auth import Login, PasswordCambiar, UsuarioCrear, UsuarioRespuesta, UsuariosPagina
from app.services.auth import (
    COOKIE_NAME, SESSION_SECONDS, UsuarioActual, administrador, comprobar_origen,
    crear_usuario, dummy_password_hash, hash_password, token_digest, verify_password,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])
usuarios_router = APIRouter(prefix="/usuarios", tags=["Usuarios"], dependencies=[Depends(administrador)])
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.post("/login", response_model=UsuarioRespuesta)
def login(data: Login, request: Request, response: Response, session: DatabaseSession):
    comprobar_origen(request)
    response.headers["Cache-Control"] = "no-store"
    try:
        with session.begin():
            cuenta = session.scalar(select(Usuario).where(Usuario.usuario == data.usuario).with_for_update())
            encoded = cuenta.password_hash if cuenta is not None else dummy_password_hash()
            valido = verify_password(data.password.get_secret_value(), encoded)
            if not valido or cuenta is None or not cuenta.activo:
                raise HTTPException(401, "Usuario o contraseña incorrectos.")
            previo = request.cookies.get(COOKIE_NAME)
            ahora = datetime.now(timezone.utc)
            if previo:
                session.execute(update(Sesion).where(Sesion.token_hash == token_digest(previo)).values(revocada_en=ahora))
            token = secrets.token_urlsafe(32)
            session.add(Sesion(token_hash=token_digest(token), usuario_id=cuenta.id,
                               creada_en=ahora, vence_en=ahora + timedelta(seconds=SESSION_SECONDS)))
            resultado = UsuarioRespuesta.model_validate(cuenta)
        response.set_cookie(COOKIE_NAME, token, max_age=SESSION_SECONDS, httponly=True,
                            secure=request.url.scheme == "https", samesite="strict", path="/")
        return resultado
    except SQLAlchemyError:
        raise HTTPException(503, "No se pudo iniciar sesión. Verifica que la base tenga la migración 0006.") from None


@router.get("/me", response_model=UsuarioRespuesta)
def me(usuario: UsuarioActual, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return usuario


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, session: DatabaseSession):
    comprobar_origen(request)
    token = request.cookies.get(COOKIE_NAME)
    try:
        with session.begin():
            if token:
                session.execute(update(Sesion).where(Sesion.token_hash == token_digest(token)).values(
                    revocada_en=datetime.now(timezone.utc)))
    except SQLAlchemyError:
        raise HTTPException(503, "No se pudo revocar la sesión. Intenta cerrar sesión nuevamente.") from None
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="strict")


@usuarios_router.post("", response_model=UsuarioRespuesta, status_code=201)
def create(data: UsuarioCrear, session: DatabaseSession):
    return crear_usuario(session, data)


@router.post("/password", status_code=204)
def cambiar_password(data: PasswordCambiar, usuario: UsuarioActual, request: Request,
                     response: Response, session: DatabaseSession):
    try:
        with session.begin():
            cuenta = session.scalar(select(Usuario).where(Usuario.id == usuario.id).with_for_update())
            ahora = datetime.now(timezone.utc)
            vigente = session.get(Sesion, token_digest(request.cookies.get(COOKIE_NAME, "")))
            if (cuenta is None or not cuenta.activo or vigente is None
                    or vigente.usuario_id != usuario.id or vigente.revocada_en is not None
                    or vigente.vence_en <= ahora):
                raise HTTPException(401, "La sesión ya no es válida. Inicia sesión nuevamente.")
            if not verify_password(data.password_actual.get_secret_value(), cuenta.password_hash):
                raise HTTPException(400, "La contraseña actual no es correcta.")
            if data.password_actual.get_secret_value() == data.password_nueva.get_secret_value():
                raise HTTPException(400, "La nueva contraseña debe ser diferente de la actual.")
            cuenta.password_hash = hash_password(data.password_nueva.get_secret_value())
            session.execute(update(Sesion).where(Sesion.usuario_id == usuario.id, Sesion.revocada_en.is_(None)).values(
                revocada_en=ahora))
    except SQLAlchemyError:
        raise HTTPException(503, "No se pudo cambiar la contraseña. Intenta nuevamente.") from None
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="strict")


@usuarios_router.get("", response_model=UsuariosPagina)
def list_all(session: DatabaseSession, offset: Annotated[int, Query(ge=0)] = 0,
             limit: Annotated[int, Query(ge=1, le=100)] = 20):
    try:
        total = session.scalar(select(func.count()).select_from(Usuario))
        items = list(session.scalars(select(Usuario).order_by(Usuario.id).offset(offset).limit(limit)))
        return {"items": items, "total": total, "offset": offset, "limit": limit}
    except SQLAlchemyError:
        raise HTTPException(503, "No se pudieron consultar los usuarios.") from None


@usuarios_router.post("/{id}/revocar-sesiones", status_code=204)
def revoke(id: Annotated[int, Path(ge=1)], session: DatabaseSession):
    try:
        with session.begin():
            if session.get(Usuario, id) is None:
                raise HTTPException(404, "Usuario no encontrado.")
            session.execute(update(Sesion).where(Sesion.usuario_id == id, Sesion.revocada_en.is_(None)).values(
                revocada_en=datetime.now(timezone.utc)))
    except SQLAlchemyError:
        raise HTTPException(503, "No se pudieron revocar las sesiones.") from None
