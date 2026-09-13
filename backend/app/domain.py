from app.models import Task, TaskStatus

MAX_WEIGHT = 100


class DomainError(ValueError):
    pass


def allocated_weight(tasks: list[Task], exclude_id=None) -> int:
    return sum(t.weight_percent for t in tasks if exclude_id is None or t.id != exclude_id)


def remaining_weight(tasks: list[Task], exclude_id=None) -> int:
    return MAX_WEIGHT - allocated_weight(tasks, exclude_id)


def assert_weight_allowed(current_sum: int, new_weight: int) -> None:
    if new_weight < 1 or new_weight > MAX_WEIGHT:
        raise DomainError("Вага етапу має бути від 1% до 100%.")
    if current_sum + new_weight > MAX_WEIGHT:
        raise DomainError(
            f"Сума ваги на цілі не може перевищувати 100% (зараз {current_sum}%, додаєте {new_weight}%)."
        )


def progress_percent(tasks: list[Task]) -> int:
    """Прогрес рахує лише етапи, які головний закрив після перевірки доказів."""
    return sum(t.weight_percent for t in tasks if t.status == TaskStatus.CLOSED)
