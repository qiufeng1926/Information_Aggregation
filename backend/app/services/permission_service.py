from datetime import datetime

from sqlalchemy.orm import Session

from app.models import User
from app.models.permission import SystemSetting, ViewAccessRequest
from app.schemas.user import ViewAccessRequestCreate
from app.utils.access_control import (
    SETTING_BLOCK_UPPER_TASKS,
    can_review_access,
    get_system_setting,
    is_super_admin,
    normalize_role,
)


class PermissionService:
    @staticmethod
    def create_access_request(db: Session, user: User, data: ViewAccessRequestCreate) -> ViewAccessRequest:
        if bool(user.view_library):
            raise ValueError("您已拥有查阅权限")

        pending = (
            db.query(ViewAccessRequest)
            .filter(ViewAccessRequest.user_id == user.id, ViewAccessRequest.status == "pending")
            .first()
        )
        if pending:
            raise ValueError("已有待审核的申请，请等待管理员处理")

        req = ViewAccessRequest(user_id=user.id, reason=data.reason, status="pending")
        db.add(req)
        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def list_access_requests(
        db: Session,
        viewer: User,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        if not can_review_access(viewer):
            query = db.query(ViewAccessRequest).filter(ViewAccessRequest.user_id == viewer.id)
        else:
            query = db.query(ViewAccessRequest)

        if status:
            query = query.filter(ViewAccessRequest.status == status)

        query = query.order_by(ViewAccessRequest.created_at.desc())
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        user_map = {
            u.id: u
            for u in db.query(User).filter(
                User.id.in_({i.user_id for i in items} | {i.reviewer_id for i in items if i.reviewer_id})
            )
        }

        result = []
        for item in items:
            u = user_map.get(item.user_id)
            result.append(
                {
                    "id": item.id,
                    "user_id": item.user_id,
                    "status": item.status,
                    "reason": item.reason,
                    "reviewer_id": item.reviewer_id,
                    "review_note": item.review_note,
                    "created_at": item.created_at,
                    "reviewed_at": item.reviewed_at,
                    "username": u.username if u else None,
                    "nickname": u.nickname if u else None,
                }
            )
        return result, total

    @staticmethod
    def review_access_request(
        db: Session,
        request_id: int,
        reviewer: User,
        approve: bool,
        review_note: str | None = None,
    ) -> ViewAccessRequest:
        if not can_review_access(reviewer):
            raise ValueError("无权审核查阅申请")

        req = db.query(ViewAccessRequest).filter(ViewAccessRequest.id == request_id).first()
        if not req:
            raise ValueError("申请不存在")
        if req.status != "pending":
            raise ValueError("该申请已处理")

        req.status = "approved" if approve else "rejected"
        req.reviewer_id = reviewer.id
        req.review_note = review_note
        req.reviewed_at = datetime.now()

        if approve:
            user = db.query(User).filter(User.id == req.user_id).first()
            if user:
                user.view_library = 1

        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def get_settings(db: Session) -> dict:
        return {
            "block_upper_role_tasks": get_system_setting(
                db, SETTING_BLOCK_UPPER_TASKS, "true"
            ).lower()
            in ("1", "true", "yes"),
        }

    @staticmethod
    def update_settings(db: Session, viewer: User, block_upper_role_tasks: bool) -> dict:
        if not can_review_access(viewer):
            raise ValueError("无权修改系统权限设置")

        row = db.query(SystemSetting).filter(SystemSetting.key == SETTING_BLOCK_UPPER_TASKS).first()
        value = "true" if block_upper_role_tasks else "false"
        if row:
            row.value = value
        else:
            db.add(SystemSetting(key=SETTING_BLOCK_UPPER_TASKS, value=value))
        db.commit()
        return PermissionService.get_settings(db)

    @staticmethod
    def revoke_library_access(db: Session, user_id: int, reviewer: User) -> User:
        if not can_review_access(reviewer):
            raise ValueError("无权操作")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("用户不存在")
        if normalize_role(user.role) != "user":
            raise ValueError("仅可撤销普通用户的查阅权限")
        user.view_library = 0
        db.commit()
        db.refresh(user)
        return user
