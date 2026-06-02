from sqlalchemy.orm import Session

from app.constants.roles import ADMIN, MANAGEABLE_ROLES, SUPER_ADMIN
from app.models import User
from app.schemas.user import UserCreate, UserUpdate
from app.utils.access_control import normalize_role
from app.utils.security import get_password_hash


class UserService:
    @staticmethod
    def list_users(db: Session, page: int, page_size: int) -> tuple[list[User], int]:
        query = db.query(User).order_by(User.id.asc())
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    @staticmethod
    def get_user(db: Session, user_id: int) -> User | None:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def create_user(db: Session, data: UserCreate, operator: User) -> User:
        role = normalize_role(data.role)
        if role not in MANAGEABLE_ROLES:
            raise ValueError("只能创建管理员或普通用户")
        if role == ADMIN and not UserService._can_assign_admin(operator):
            raise ValueError("无权创建管理员账号")

        exists = db.query(User).filter(User.username == data.username).first()
        if exists:
            raise ValueError("用户名已存在")

        user = User(
            username=data.username,
            password_hash=get_password_hash(data.password),
            nickname=data.nickname or data.username,
            role=role,
            status=1,
            view_library=0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_user(db: Session, user_id: int, data: UserUpdate, operator: User) -> User:
        user = UserService.get_user(db, user_id)
        if not user:
            raise ValueError("用户不存在")

        target_is_super = normalize_role(user.role) == SUPER_ADMIN
        if target_is_super and user.id != operator.id:
            raise ValueError("不能修改其他超级管理员")
        if user.id == operator.id and data.status == 0:
            raise ValueError("不能禁用自己")

        if data.role is not None:
            new_role = normalize_role(data.role)
            if new_role == SUPER_ADMIN:
                raise ValueError("不能通过此接口设置超级管理员角色")
            if target_is_super:
                raise ValueError("不能修改超级管理员角色")
            if new_role not in MANAGEABLE_ROLES:
                raise ValueError("无效的角色")
            if new_role == ADMIN and not UserService._can_assign_admin(operator):
                raise ValueError("无权设置管理员角色")
            user.role = new_role

        if data.nickname is not None:
            user.nickname = data.nickname
        if data.status is not None:
            user.status = data.status
        if data.view_library is not None and not target_is_super:
            user.view_library = 1 if data.view_library else 0
        if data.password:
            user.password_hash = get_password_hash(data.password)

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete_user(db: Session, user_id: int, operator: User) -> None:
        user = UserService.get_user(db, user_id)
        if not user:
            raise ValueError("用户不存在")
        if user.id == operator.id:
            raise ValueError("不能删除自己")
        if normalize_role(user.role) == SUPER_ADMIN:
            raise ValueError("不能删除超级管理员")
        db.delete(user)
        db.commit()

    @staticmethod
    def _can_assign_admin(operator: User) -> bool:
        return normalize_role(operator.role) == SUPER_ADMIN

    @staticmethod
    def to_out(user: User) -> dict:
        return {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "role": normalize_role(user.role),
            "status": user.status,
            "view_library": bool(user.view_library),
            "created_at": user.created_at,
        }
