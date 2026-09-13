from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Goal, GoalMember, Task, User, UserRole


def is_goal_owner(user: User, goal: Goal) -> bool:
    return goal.owner_id == user.id or user.role == UserRole.OWNER and goal.owner_id == user.id


def is_member(db: Session, user: User, goal: Goal) -> bool:
    if goal.owner_id == user.id:
        return True
    row = (
        db.query(GoalMember)
        .filter(GoalMember.goal_id == goal.id, GoalMember.user_id == user.id)
        .one_or_none()
    )
    return row is not None


def require_goal(db: Session, goal_id) -> Goal:
    goal = db.get(Goal, goal_id)
    if goal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ціль не знайдено")
    return goal


def require_task(db: Session, task_id) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Етап не знайдено")
    return task


def require_owner(user: User, goal: Goal) -> None:
    if goal.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Лише головний цієї цілі")


def require_member(db: Session, user: User, goal: Goal) -> None:
    if not is_member(db, user, goal):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Немає доступу до цієї цілі")
