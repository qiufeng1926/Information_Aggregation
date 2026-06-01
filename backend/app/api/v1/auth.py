from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import DbSession, get_current_user
from app.models import User
from app.schemas import ResponseBase, Token, UserInfo
from app.utils.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=ResponseBase[Token])
def login(db: DbSession, form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if user.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已禁用")

    token = create_access_token(subject=user.username)
    return ResponseBase(data=Token(access_token=token))


@router.get("/me", response_model=ResponseBase[UserInfo])
def get_me(current_user: User = Depends(get_current_user)):
    return ResponseBase(data=UserInfo.model_validate(current_user))
