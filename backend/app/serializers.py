from __future__ import annotations

from app.domain import allocated_weight, progress_percent, remaining_weight
from app.models import Evidence, EvidenceFile, Goal, Task, TaskStatus, User
from app.schemas import EvidenceOut, FileOut, GoalDetailOut, GoalListOut, TaskOut, UserOut


def display_name(user: User) -> str:
    parts = [user.first_name]
    if user.last_name:
        parts.append(user.last_name)
    return " ".join(parts)


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role.value,
        display_name=display_name(user),
    )


def file_out(file: EvidenceFile) -> FileOut:
    return FileOut(
        id=file.id,
        original_name=file.original_name,
        mime_type=file.mime_type,
        kind=file.kind.value,
        url=f"/api/uploads/{file.id}",
    )


def evidence_out(item: Evidence) -> EvidenceOut:
    return EvidenceOut(
        id=item.id,
        proof_note=item.proof_note,
        created_at=item.created_at,
        uploaded_by=user_out(item.uploaded_by),
        files=[file_out(f) for f in item.files],
    )


def latest_evidence(task: Task) -> Evidence | None:
    if not task.evidence:
        return None
    return max(task.evidence, key=lambda e: e.created_at)


def task_out(task: Task) -> TaskOut:
    latest = latest_evidence(task)
    return TaskOut(
        id=task.id,
        goal_id=task.goal_id,
        goal_name=task.goal.name if task.goal else "",
        title=task.title,
        description=task.description,
        weight_percent=task.weight_percent,
        status=task.status.value,
        assignee=user_out(task.assignee),
        reject_reason=task.reject_reason,
        created_at=task.created_at,
        closed_at=task.closed_at,
        latest_evidence=evidence_out(latest) if latest else None,
    )


def _unique_tasks(goal: Goal) -> list[Task]:
    seen: dict = {}
    for task in goal.tasks:
        seen[task.id] = task
    return list(seen.values())


def goal_list_out(goal: Goal) -> GoalListOut:
    tasks = _unique_tasks(goal)
    return GoalListOut(
        id=goal.id,
        name=goal.name,
        description=goal.description,
        progress_percent=progress_percent(tasks),
        allocated_weight=allocated_weight(tasks),
        remaining_weight=remaining_weight(tasks),
        pending_reviews=sum(1 for t in tasks if t.status == TaskStatus.AWAITING_REVIEW),
        members_count=len({m.user_id: m for m in goal.members}),
        created_at=goal.created_at,
    )


def goal_detail_out(goal: Goal, tasks: list[Task]) -> GoalDetailOut:
    base = goal_list_out(goal)
    members = [user_out(m.user) for m in {m.user_id: m for m in goal.members}.values()]
    return GoalDetailOut(
        **base.model_dump(),
        owner=user_out(goal.owner),
        members=members,
        tasks=[task_out(t) for t in tasks],
    )
