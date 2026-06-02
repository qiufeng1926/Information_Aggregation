from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants.roles import ALL_ROLES


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nickname: str | None
    role: str
    status: int
    view_library: bool = False
    created_at: datetime


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名至少 3 个字符")
    password: str = Field(..., min_length=8, max_length=128, description="密码至少 8 位")
    nickname: str | None = None
    role: str = Field(default="user", description="admin/user")


class UserUpdate(BaseModel):
    nickname: str | None = None
    role: str | None = None
    status: int | None = None
    view_library: bool | None = None
    password: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str | None) -> str | None:
        if password is None or password == "":
            return None
        if len(password) < 8:
            raise ValueError("密码至少 8 位")
        return password


class ViewAccessRequestCreate(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class ViewAccessRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: str
    reason: str | None
    reviewer_id: int | None
    review_note: str | None
    created_at: datetime
    reviewed_at: datetime | None
    username: str | None = None
    nickname: str | None = None


class AccessReviewAction(BaseModel):
    approve: bool
    review_note: str | None = None


class SystemSettingOut(BaseModel):
    block_upper_role_tasks: bool = True
