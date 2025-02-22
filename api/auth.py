from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from services.users import UsersService
from core.security import create_access_token, get_current_user
from tables import User
from database import get_session
from passlib.hash import bcrypt
from datetime import timedelta
from models import auth


router = APIRouter(
    prefix="/api/auth",
    tags=["Auth"],
)


@router.post("/register", status_code=201)
def register(
    data: auth.UserRegistation,
    db: Session = Depends(get_session),
):
    # Hash the password
    hashed_password = bcrypt.hash(data.password)
    password_salt = hashed_password[:29]

    # Create the user
    users_service = UsersService(db)
    user = users_service.create_user(
        email=data.email,
        password_hash=hashed_password,
        password_salt=password_salt,
        name=data.name,
    )

    return {
        "id": user.id,
        "email": user.email,
    }


@router.post("/login")
def login(data: auth.UserLogin, db: Session = Depends(get_session)):
    user = (
        db.query(User)
        .filter(User.email == data.email, User.is_active == True)
        .first()
    )
    if not user or not bcrypt.verify(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=timedelta(minutes=4320)
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
    }
