"""采集模块访问控制"""

from app.models import User


def is_admin(user: User) -> bool:
    return user.role == "admin"
