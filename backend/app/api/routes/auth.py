from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import AuthState, Credentials
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])
Db = Annotated[Session, Depends(get_db)]


@router.get("/state")
def auth_state(db: Db, request: Request, response: Response) -> AuthState:
    response.headers["Cache-Control"] = "no-store"
    return auth.state(db, request)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: Credentials, db: Db, request: Request, response: Response) -> AuthState:
    return auth.register(db, data, request, response)


@router.post("/login")
def login(data: Credentials, db: Db, request: Request, response: Response) -> AuthState:
    return auth.login(db, data, request, response)


@router.post("/logout")
def logout(db: Db, request: Request, response: Response) -> AuthState:
    return auth.logout(db, request, response)
