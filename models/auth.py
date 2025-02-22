from pydantic import BaseModel
from uuid import UUID
from typing import Union, List, Optional


class UserRegistation(BaseModel):
    email: str
    password: str
    name: str

    class Config:
        orm_mode = True


class UserLogin(BaseModel):
    email: str
    password: str

    class Config:
        orm_mode = True
