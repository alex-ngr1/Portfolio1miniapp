import type { Task, TaskStatus, User } from "./api";

export function esc(value: string | number | null | undefined): string {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function initials(user: User): string {
  const a = user.first_name?.[0] ?? "?";
  const b = user.last_name?.[0] ?? "";
  return (a + b).toUpperCase();
}

export const STATUS: Record<TaskStatus, { label: string; cls: string }> = {
  open: { label: "Відкритий", cls: "open" },
  awaiting_review: { label: "На перевірці", cls: "wait" },
  closed: { label: "Закритий", cls: "ok" },
};

export function statusChip(status: TaskStatus): string {
  const s = STATUS[status];
  return `<span class="chip ${s.cls}">${s.label}</span>`;
}

export function person(user: User): string {
  return `<span class="avatar"><span class="dot">${esc(initials(user))}</span>${esc(user.display_name)}</span>`;
}

export function taskLine(task: Task): string {
  return `
    <article class="stage" data-go="#/tasks/${task.id}">
      <div class="weight">${task.weight_percent}%</div>
      <div>
        <h3>${esc(task.title)}</h3>
        <div class="muted">${esc(task.assignee.display_name)}</div>
      </div>
      ${statusChip(task.status)}
    </article>`;
}

export function screen(html: string): string {
  return html;
}
