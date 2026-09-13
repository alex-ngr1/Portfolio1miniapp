from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.access import require_goal, require_member, require_owner
from app.auth import current_user
from app.db import get_db
from app.domain import assert_weight_allowed, DomainError
from app.invites import add_member, generate_code, redeem_code
from app.models import Evidence, Goal, GoalMember, Invite, Task, User, UserRole
from app.schemas import GoalCreate, GoalDetailOut, GoalListOut, InviteCreate, InviteOut, InviteRedeem, TaskCreate, TaskOut
from app.serializers import goal_detail_out, goal_list_out, task_out

router = APIRouter(prefix="/api", tags=["goals"])


def _weight_sum(db: Session, goal_id) -> int:
    total = (
        db.query(func.coalesce(func.sum(Task.weight_percent), 0))
        .filter(Task.goal_id == goal_id)
        .scalar()
    )
    return int(total or 0)


def _goal_query(db: Session):
    return db.query(Goal).options(
        joinedload(Goal.owner),
        selectinload(Goal.members).selectinload(GoalMember.user),
        selectinload(Goal.tasks).selectinload(Task.assignee),
        selectinload(Goal.tasks).selectinload(Task.evidence).selectinload(Evidence.files),
        selectinload(Goal.tasks).selectinload(Task.evidence).selectinload(Evidence.uploaded_by),
        selectinload(Goal.tasks).joinedload(Task.goal),
    )


@router.get("/me")
def me(user: Annotated[User, Depends(current_user)]) -> dict:
    from app.serializers import user_out

    return {"user": user_out(user)}


@router.get("/goals", response_model=list[GoalListOut])
def list_goals(user: Annotated[User, Depends(current_user)], db: Annotated[Session, Depends(get_db)]):
    q = _goal_query(db)
    if user.role == UserRole.OWNER:
        goals = q.filter(Goal.owner_id == user.id).order_by(Goal.created_at.desc()).all()
    else:
        member_ids = db.query(GoalMember.goal_id).filter(GoalMember.user_id == user.id)
        goals = q.filter(Goal.id.in_(member_ids)).order_by(Goal.created_at.desc()).all()
    return [goal_list_out(g) for g in goals]


@router.post("/goals", response_model=GoalDetailOut, status_code=201)
def create_goal(
    body: GoalCreate,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if user.role != UserRole.OWNER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ціль створює лише головний")
    goal = Goal(name=body.name.strip(), description=body.description, owner_id=user.id)
    db.add(goal)
    db.commit()
    goal = _goal_query(db).filter(Goal.id == goal.id).one()
    return goal_detail_out(goal, [])


@router.get("/goals/{goal_id}", response_model=GoalDetailOut)
def get_goal(
    goal_id: uuid.UUID,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    goal = _goal_query(db).filter(Goal.id == goal_id).one_or_none()
    if goal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ціль не знайдено")
    require_member(db, user, goal)
    tasks = list({t.id: t for t in goal.tasks}.values())
    if goal.owner_id != user.id:
        tasks = [t for t in tasks if t.assignee_id == user.id]
    tasks.sort(key=lambda t: t.created_at)
    return goal_detail_out(goal, tasks)


@router.get("/my/tasks", response_model=list[TaskOut])
def my_tasks(user: Annotated[User, Depends(current_user)], db: Annotated[Session, Depends(get_db)]):
    tasks = (
        db.query(Task)
        .options(
            joinedload(Task.assignee),
            joinedload(Task.goal),
            joinedload(Task.evidence).joinedload(Evidence.files),
            joinedload(Task.evidence).joinedload(Evidence.uploaded_by),
        )
        .filter(Task.assignee_id == user.id)
        .order_by(Task.created_at.desc())
        .all()
    )
    return [task_out(t) for t in tasks]


@router.post("/goals/{goal_id}/tasks", response_model=TaskOut, status_code=201)
def create_task(
    goal_id: uuid.UUID,
    body: TaskCreate,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    goal = require_goal(db, goal_id)
    require_member(db, user, goal)
    assignee_id = body.assignee_id or user.id
    assignee = db.get(User, assignee_id)
    if assignee is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Виконавця не знайдено")
    if assignee_id != user.id and goal.owner_id != user.id:
        # працівник може ставити етап на себе або на колегу з цілі
        from app.access import is_member

        if not is_member(db, assignee, goal) and assignee.id != goal.owner_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Призначити можна лише учасника цілі")
    try:
        assert_weight_allowed(_weight_sum(db, goal.id), body.weight_percent)
    except DomainError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    task = Task(
        goal_id=goal.id,
        title=body.title.strip(),
        description=body.description,
        weight_percent=body.weight_percent,
        assignee_id=assignee_id,
        created_by_id=user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    task.goal = goal
    task.assignee = assignee
    return task_out(task)


@router.post("/goals/{goal_id}/invites", response_model=InviteOut)
def create_invite(
    goal_id: uuid.UUID,
    body: InviteCreate,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    goal = require_goal(db, goal_id)
    require_owner(user, goal)
    added = False
    if body.telegram_id:
        existing = db.query(User).filter(User.telegram_id == body.telegram_id).one_or_none()
        if existing:
            added = add_member(db, goal, existing)
    invite = Invite(
        goal_id=goal.id,
        code=generate_code(),
        telegram_id=body.telegram_id,
        created_by_id=user.id,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return InviteOut(
        id=invite.id,
        code=invite.code,
        telegram_id=invite.telegram_id,
        used=invite.used_at is not None,
        added_immediately=added,
    )


@router.post("/invites/redeem")
def redeem_invite(
    body: InviteRedeem,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        goal = redeem_code(db, user, body.code)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"goal_id": str(goal.id), "name": goal.name}
