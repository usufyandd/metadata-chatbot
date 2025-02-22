from sqlalchemy.orm import Session
from sqlalchemy import or_
from tables import User
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status
import uuid
from uuid import UUID
from models.users import UserCreate, UserUpdate, ChangePasswordRequest
from datetime import datetime
from core.security import get_password_hash, verify_password
from typing import List, Optional, Tuple

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UsersService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(
        self,
        email: str,
        password_hash: str,
        password_salt: str,
        name: str,
        is_active: bool = True,
    ):
        # Check if the email already exists
        if self.db.query(User).filter(User.email == email).first():
            raise HTTPException(
                status_code=400, detail="Email already registered."
            )

        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=password_hash,
            password_salt=password_salt,
            name=name,
            is_active=is_active,
        )
        self.db.add(user)

        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user(self, user_id: str) -> dict:
        # Fetch the user with related role
        user = (
            self.db.query(User)
            .filter(User.id == user_id, User.is_active == True)
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Construct the final output
        user_data = {
            "email": user.email,
            "name": user.name,
            "id": user.id,
            "is_active": user.is_active,
            "last_login": user.last_login,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

        return user_data

    def list_users(
        self,
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        current_user_id: UUID = None,
    ) -> Tuple[List[dict], int]:

        query = self.db.query(
            User,
        ).filter(User.is_active == True)

        # Apply filters
        if search:
            search_pattern = search.strip()
            search_pattern = f"%{search}%"
            query = query.filter(
                User.name.ilike(search_pattern)
                | User.email.ilike(search_pattern)
            )

        # Total count
        total = query.count()

        # Pagination
        users = query.offset(skip).limit(limit).all()

        # Format response
        result = []
        for user in users:
            result.append(
                {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "created_at": user.created_at,
                    "is_active": user.is_active,
                }
            )

        return result, total

    def update_user(self, data: UserUpdate):
        user = self.db.query(User).filter(User.id == data.id).first()
        # Check if the user exists
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if data.email and data.email != user.email:
            if self.db.query(User).filter(User.email == data.email).first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )
            user.email = data.email

        if data.name:
            user.name = data.name


        self.db.commit()
        self.db.refresh(user)
        return user

    def change_password(
        self, data: ChangePasswordRequest, current_user: User
    ) -> User:
        user = current_user

        if not verify_password(data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password",
            )

        password_hash, password_salt = get_password_hash(data.new_password)
        user.password_hash = password_hash
        user.password_salt = password_salt

        self.db.commit()
        self.db.refresh(user)
        return user

    def deactivate_user(self, id):
        user = self.db.query(User).filter(User.id == id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        user.is_active = False
        user.updated_at = datetime.utcnow()
        self.db.commit()
        return "User deactivated successfully"
