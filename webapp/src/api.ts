export type Role = "owner" | "worker";

export type User = {
  id: string;
  telegram_id: number;
  username: string | null;
  first_name: string;
  last_name: string | null;
  role: Role;
  display_name: string;
};

export type FileOut = {
  id: string;
  original_name: string;
  mime_type: string;
  kind: "photo" | "video";
  url: string;
};

export type Evidence = {
  id: string;
  proof_note: string;
  created_at: string;
  uploaded_by: User;
  files: FileOut[];
};

export type TaskStatus = "open" | "awaiting_review" | "closed";

export type Task = {
  id: string;
  goal_id: string;
  goal_name: string;
  title: string;
  description: string | null;
  weight_percent: number;
  status: TaskStatus;
  assignee: User;
  reject_reason: string | null;
  created_at: string;
  closed_at: string | null;
  latest_evidence: Evidence | null;
};

export type GoalList = {
  id: string;
  name: string;
  description: string | null;
  progress_percent: number;
  allocated_weight: number;
  remaining_weight: number;
  pending_reviews: number;
  members_count: number;
  created_at: string;
};

export type GoalDetail = GoalList & {
  owner: User;
  members: User[];
  tasks: Task[];
};

const TOKEN_KEY = "tsilnyk_token";

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

export function mediaUrl(path: string): string {
  const token = getToken();
  const sep = path.includes("?") ? "&" : "?";
  return token ? `${path}${sep}token=${encodeURIComponent(token)}` : path;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(path, { ...init, headers });
  if (res.status === 401) {
    clearToken();
    throw new Error("Потрібен повторний вхід");
  }
  if (!res.ok) {
    let detail = `Помилка ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  telegramAuth: (initData: string) =>
    request<{ token: string; user: User; demo: boolean }>("/api/auth/telegram", {
      method: "POST",
      body: JSON.stringify({ initData }),
    }),
  demoAuth: (asRole: "owner" | "worker") =>
    request<{ token: string; user: User; demo: boolean }>("/api/auth/demo", {
      method: "POST",
      body: JSON.stringify({ as: asRole }),
    }),
  me: () => request<{ user: User }>("/api/me"),
  goals: () => request<GoalList[]>("/api/goals"),
  goal: (id: string) => request<GoalDetail>(`/api/goals/${id}`),
  createGoal: (name: string, description: string) =>
    request<GoalDetail>("/api/goals", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    }),
  createTask: (goalId: string, payload: { title: string; description?: string; weight_percent: number }) =>
    request<Task>(`/api/goals/${goalId}/tasks`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  invite: (goalId: string, telegram_id?: number) =>
    request<{ code: string; added_immediately: boolean; telegram_id: number | null }>(
      `/api/goals/${goalId}/invites`,
      { method: "POST", body: JSON.stringify({ telegram_id: telegram_id || null }) },
    ),
  redeem: (code: string) =>
    request<{ goal_id: string; name: string }>("/api/invites/redeem", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
  myTasks: () => request<Task[]>("/api/my/tasks"),
  task: (id: string) => request<Task>(`/api/tasks/${id}`),
  uploadEvidence: (taskId: string, note: string, files: File[]) => {
    const data = new FormData();
    data.append("proof_note", note);
    for (const file of files) data.append("files", file);
    return request<Task>(`/api/tasks/${taskId}/evidence`, { method: "POST", body: data });
  },
  closeTask: (taskId: string) => request<Task>(`/api/tasks/${taskId}/close`, { method: "POST" }),
  rejectTask: (taskId: string, reason: string) =>
    request<Task>(`/api/tasks/${taskId}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
};
