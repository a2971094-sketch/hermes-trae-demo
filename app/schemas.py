"""请求/响应 Schema"""

from pydantic import BaseModel, Field, ConfigDict


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterResponse(BaseModel):
    user_id: int


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    created_at: str


class UserListResponse(BaseModel):
    users: list[UserResponse]
