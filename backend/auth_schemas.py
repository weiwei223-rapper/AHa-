import os
import bcrypt
import unicodedata
from typing import Optional
from pydantic import BaseModel, validator
import schema

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def validate_user_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError('姓名不得為空。')
    if len(cleaned) < 2:
        raise ValueError('姓名長度至少為 2 個字元。')

    allowed_extra = set(" .'-")
    for char in cleaned:
        category = unicodedata.category(char)
        if category.startswith(('L', 'M', 'N')):
            continue
        if char in allowed_extra or char.isspace():
            continue
        raise ValueError('姓名僅能包含文字、數字、空白、點、撇號或連字號。')

    return cleaned

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    user: schema.UserResponse
    message: str
    access_token: str
    token_type: str = "bearer"

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

    @validator('name')
    def validate_name(cls, value: str) -> str:
        return validate_user_name(value)

class OTPRequest(BaseModel):
    email: str

class OTPVerifyRequest(BaseModel):
    otp_token: str
    otp: str

class OTPVerifyResponse(BaseModel):
    reset_token: str
    message: str

class PasswordResetRequest(BaseModel):
    reset_token: str
    new_password: str
