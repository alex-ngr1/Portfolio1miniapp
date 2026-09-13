import "./styles.css";
import {
  api,
  clearToken,
  getToken,
  mediaUrl,
  setToken,
  type GoalDetail,
  type GoalList,
  type Task,
  type User,
} from "./api";
import { bootTelegram, haptic, hasTelegramUser, tg } from "./telegram";
import { esc, person, statusChip, taskLine } from "./ui";

const root = document.querySelector("#app") as HTMLElement;
let me: User | null = null;
let error = "";

function route(): string {
  return location.hash.replace(/^#/, "") || "/";
}

function go(path: string): void {
  location.hash = path.startsWith("#") ? path : `#${path}`;
}

function backBtn(fallback = "#/"): string {
  return `<button class="back" data-go="${fallback}">← Назад</button>`;
}

function who(): string {
  if (!me) return "";
  const role = me.role === "owner" ? "Головний" : "Виконавець";
  return `<div class="who"><strong>${esc(me.display_name)}</strong>${esc(role)}<div class="role-pill">${role}</div></div>`;
}

function bindNav(el: HTMLElement): void {
  el.querySelectorAll<HTMLElement>("[data-go]").forEach((node) => {
    node.addEventListener("click", () => {
      haptic("light");
      go(node.dataset.go || "/");
    });
  });
}

async function ensureAuth(): Promise<boolean> {
  if (!getToken()) {
    if (hasTelegramUser() && tg) {
      const res = await api.telegramAuth(tg.initData);
      setToken(res.token);
      me = res.user;
      return true;
    }
    return false;
  }
  const res = await api.me();
  me = res.user;
  return true;
}

function gate(): string {
  return `
    <section class="gate">
      <div class="muted">Міні-застосунок команди</div>
      <h1>Цільник</h1>
      <p class="muted">Ціль ділиться на етапи з вагою. Відсоток іде в прогрес лише після того, як головний закриє докази.</p>
      <div class="pick">
        <button data-demo="owner">
          <b>Я головний</b>
          <span class="muted">Цілі, команда, перевірка доказів, закриття етапів</span>
        </button>
        <button data-demo="worker">
          <b>Я виконавець</b>
          <span class="muted">Мої етапи, фото/відео і примітка що все працює</span>
        </button>
      </div>
      <p class="muted" style="margin-top:18px">У Telegram вхід іде автоматично з initData. Тут демо, щоб відкрити сид «Будинок №24».</p>
      ${error ? `<div class="err">${esc(error)}</div>` : ""}
    </section>`;
}

function ownerHome(goals: Awaited<ReturnType<typeof api.goals>>): string {
  const cards = goals
    .map(
      (g) => `
      <article class="card" data-go="#/goals/${g.id}">
        <div class="card-head">
          <div>
            <h3>${esc(g.name)}</h3>
            <div class="muted">${g.members_count} у команді · ${g.allocated_weight}% розкладено</div>
          </div>
          <div class="pct">${g.progress_percent}%</div>
        </div>
        <div class="bar"><i style="width:${g.progress_percent}%"></i></div>
        <div class="row">
          ${g.pending_reviews ? `<span class="chip wait">${g.pending_reviews} на перевірці</span>` : `<span class="chip">Немає черги</span>`}
        </div>
      </article>`,
    )
    .join("");
  return `
    <div class="top"><div class="brand"><b>Цілі</b><span class="muted">Закриваєте лише перевірену роботу</span></div>${who()}</div>
    ${cards || `<div class="empty">Ще немає цілей</div>`}
    <div class="actions"><button class="btn" data-go="#/goals/new">Нова ціль</button></div>`;
}

function workerHome(tasks: Task[], goals: GoalList[]): string {
  const open = tasks.filter((t) => t.status !== "closed");
  const done = tasks.filter((t) => t.status === "closed");
  const goalCards = goals
    .map(
      (g) => `
      <article class="card" data-go="#/goals/${g.id}">
        <div class="card-head">
          <div>
            <h3>${esc(g.name)}</h3>
            <div class="muted">Вільна вага ${g.remaining_weight}%</div>
          </div>
          <div class="pct">${g.progress_percent}%</div>
        </div>
        <div class="bar"><i style="width:${g.progress_percent}%"></i></div>
      </article>`,
    )
    .join("");
  return `
    <div class="top"><div class="brand"><b>Мої етапи</b><span class="muted">Ви бачите лише свою роботу</span></div>${who()}</div>
    <div class="section"><h2>У роботі</h2></div>
    ${open.map(taskLine).join("") || `<div class="empty">Немає відкритих етапів</div>`}
    <div class="section"><h2>Цілі команди</h2></div>
    ${goalCards || `<div class="empty">Немає цілей — введіть код запрошення</div>`}
    <div class="section"><h2>Закриті</h2></div>
    ${done.map(taskLine).join("") || `<div class="empty">Порожньо</div>`}
    <div class="actions">
      <button class="btn-ghost" data-go="#/join">Код запрошення</button>
    </div>`;
}

function goalView(goal: GoalDetail, owner: boolean): string {
  const pending = goal.tasks.filter((t) => t.status === "awaiting_review");
  const stages = goal.tasks
    .slice()
    .sort((a, b) => a.created_at.localeCompare(b.created_at))
    .map(taskLine)
    .join("");
  return `
    ${backBtn("#/")}
    <section class="hero">
      <div class="kicker">Ціль</div>
      <h1>${esc(goal.name)}</h1>
      <p class="muted">${esc(goal.description || "")}</p>
      <div class="bar"><i style="width:${goal.progress_percent}%"></i></div>
      <div class="metrics">
        <div class="metric"><b>${goal.progress_percent}%</b><span>зараховано</span></div>
        <div class="metric"><b>${goal.pending_reviews}</b><span>на перевірці</span></div>
        <div class="metric"><b>${goal.remaining_weight}%</b><span>вільна вага</span></div>
      </div>
    </section>
    ${
      owner && pending.length
        ? `<div class="section"><h2>Черга перевірки</h2></div>${pending.map(taskLine).join("")}`
        : ""
    }
    <div class="section"><h2>Етапи</h2><span class="muted">${goal.allocated_weight}/100%</span></div>
    ${stages || `<div class="empty">Етапів ще немає</div>`}
    <div class="section"><h2>Команда</h2></div>
    <div class="people">${[goal.owner, ...goal.members].map(person).join("")}</div>
    <div class="actions">
      ${
        owner
          ? `<button class="btn" data-go="#/goals/${goal.id}/invite">Запросити виконавця</button>`
          : `<button class="btn" data-go="#/goals/${goal.id}/tasks/new">Додати етап</button>`
      }
    </div>`;
}

function newGoal(): string {
  return `
    ${backBtn("#/")}
    <h1>Нова ціль</h1>
    <p class="muted">Назва проєкту або будинку. Виконавці потім розкладуть її на етапи з вагою.</p>
    <label>Назва</label>
    <input id="name" placeholder="Наприклад, Будинок №12" />
    <label>Коротко про що</label>
    <textarea id="desc" placeholder="Що має статись, коли ціль закрита"></textarea>
    ${error ? `<div class="err">${esc(error)}</div>` : ""}
    <div class="actions"><button class="btn" id="save">Створити</button></div>`;
}

function newTask(goal: GoalDetail): string {
  return `
    ${backBtn(`#/goals/${goal.id}`)}
    <h1>Новий етап</h1>
    <p class="muted">Вага — частка цілі. На «${esc(goal.name)}» лишилось ${goal.remaining_weight}%.</p>
    <label>Назва етапу</label>
    <input id="title" placeholder="Наприклад, Штукатурка стін" />
    <label>Вага, %</label>
    <input id="weight" type="number" min="1" max="${goal.remaining_weight || 100}" value="${Math.min(20, goal.remaining_weight || 20)}" />
    <label>Що вважається готовим</label>
    <textarea id="desc" placeholder="Критерій приймання"></textarea>
    ${error ? `<div class="err">${esc(error)}</div>` : ""}
    <div class="actions"><button class="btn" id="save">Додати етап</button></div>`;
}

function inviteView(goal: GoalDetail, code?: string): string {
  return `
    ${backBtn(`#/goals/${goal.id}`)}
    <h1>Запросити</h1>
    <p class="muted">Telegram user id або одноразовий код. Код згорає після входу.</p>
    <label>Telegram user id</label>
    <input id="tgid" inputmode="numeric" placeholder="123456789" />
    ${error ? `<div class="err">${esc(error)}</div>` : ""}
    <div class="actions"><button class="btn" id="save">Створити запрошення</button></div>
    ${code ? `<div class="section"><h2>Код</h2></div><div class="card code">${esc(code)}</div>` : ""}`;
}

function joinView(): string {
  return `
    ${backBtn("#/")}
    <h1>Код запрошення</h1>
    <label>Одноразовий код</label>
    <input id="code" placeholder="Наприклад, 7K3M2Q9P" style="text-transform:uppercase" />
    ${error ? `<div class="err">${esc(error)}</div>` : ""}
    <div class="actions"><button class="btn" id="save">Приєднатись</button></div>`;
}

function gallery(task: Task): string {
  const files = task.latest_evidence?.files ?? [];
  if (!files.length) return "";
  const items = files
    .map((f) => {
      const src = mediaUrl(f.url);
      return f.kind === "video"
        ? `<video src="${src}" controls></video>`
        : `<img src="${src}" alt="${esc(f.original_name)}" />`;
    })
    .join("");
  return `<div class="gallery">${items}</div>`;
}

function taskView(task: Task, owner: boolean): string {
  const mine = me?.id === task.assignee.id;
  const ev = task.latest_evidence;
  return `
    ${backBtn(owner ? `#/goals/${task.goal_id}` : "#/")}
    <section class="hero">
      <div class="kicker">${esc(task.goal_name)}</div>
      <h1>${esc(task.title)}</h1>
      <p class="muted">${esc(task.description || "")}</p>
      <div class="row">${statusChip(task.status)}<span class="chip">${task.weight_percent}% цілі</span></div>
    </section>
    <div class="people">${person(task.assignee)}</div>
    ${
      task.reject_reason
        ? `<div class="note danger"><b>Відхилено. </b>${esc(task.reject_reason)}</div>`
        : ""
    }
    ${
      ev
        ? `<div class="section"><h2>Докази</h2></div>
           ${gallery(task)}
           <div class="note"><b>Перевірка: </b>${esc(ev.proof_note)}</div>`
        : `<div class="empty">Доказів ще немає — етап не зрушить прогрес</div>`
    }
    ${
      mine && task.status !== "closed"
        ? `<div class="section"><h2>Завантажити докази</h2></div>
           <label class="file-btn">Фото або відео
             <input id="files" type="file" accept="image/*,video/*" multiple />
           </label>
           <div id="picked" class="muted"></div>
           <label>Примітка про перевірку</label>
           <textarea id="note" placeholder="Що саме перевірили і що працює як треба"></textarea>
           <div class="actions"><button class="btn" id="upload">Надіслати на перевірку</button></div>`
        : ""
    }
    ${
      owner && task.status === "awaiting_review"
        ? `<div class="actions two">
             <button class="btn-danger" id="reject">Відхилити</button>
             <button class="btn" id="close">Закрити етап</button>
           </div>`
        : ""
    }
    ${error ? `<div class="err">${esc(error)}</div>` : ""}`;
}

async function render(): Promise<void> {
  error = "";
  root.innerHTML = `<p class="muted">Завантаження…</p>`;
  try {
    const path = route();
    const authed = await ensureAuth();
    if (!authed) {
      root.innerHTML = gate();
      root.querySelectorAll<HTMLButtonElement>("[data-demo]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          try {
            const res = await api.demoAuth(btn.dataset.demo as "owner" | "worker");
            setToken(res.token);
            me = res.user;
            haptic("success");
            go("/");
            await render();
          } catch (e) {
            error = (e as Error).message;
            root.innerHTML = gate();
          }
        });
      });
      return;
    }

    if (path === "/" && me?.role === "owner") {
      root.innerHTML = ownerHome(await api.goals());
    } else if (path === "/" && me?.role === "worker") {
      const [tasks, goals] = await Promise.all([api.myTasks(), api.goals()]);
      root.innerHTML = workerHome(tasks, goals);
    } else if (path === "/goals/new") {
      root.innerHTML = newGoal();
      root.querySelector("#save")?.addEventListener("click", async () => {
        const name = (root.querySelector("#name") as HTMLInputElement).value.trim();
        const description = (root.querySelector("#desc") as HTMLTextAreaElement).value.trim();
        try {
          const goal = await api.createGoal(name, description);
          haptic("success");
          go(`/goals/${goal.id}`);
        } catch (e) {
          error = (e as Error).message;
          root.innerHTML = newGoal();
          bindNav(root);
        }
      });
    } else if (path.startsWith("/goals/") && path.endsWith("/invite")) {
      const id = path.split("/")[2];
      const goal = await api.goal(id);
      let code = "";
      const paint = () => {
        root.innerHTML = inviteView(goal, code);
        bindNav(root);
        root.querySelector("#save")?.addEventListener("click", async () => {
          const raw = (root.querySelector("#tgid") as HTMLInputElement).value.trim();
          try {
            const inv = await api.invite(id, raw ? Number(raw) : undefined);
            code = inv.code;
            haptic("success");
            paint();
          } catch (e) {
            error = (e as Error).message;
            paint();
          }
        });
      };
      paint();
    } else if (path.startsWith("/goals/") && path.endsWith("/tasks/new")) {
      const id = path.split("/")[2];
      const goal = await api.goal(id);
      root.innerHTML = newTask(goal);
      root.querySelector("#save")?.addEventListener("click", async () => {
        const title = (root.querySelector("#title") as HTMLInputElement).value.trim();
        const weight = Number((root.querySelector("#weight") as HTMLInputElement).value);
        const description = (root.querySelector("#desc") as HTMLTextAreaElement).value.trim();
        try {
          await api.createTask(id, { title, description, weight_percent: weight });
          haptic("success");
          go(`/goals/${id}`);
        } catch (e) {
          error = (e as Error).message;
          root.innerHTML = newTask(goal);
          bindNav(root);
        }
      });
    } else if (path.startsWith("/goals/")) {
      const id = path.split("/")[2];
      const goal = await api.goal(id);
      root.innerHTML = goalView(goal, me?.role === "owner");
    } else if (path.startsWith("/tasks/")) {
      const id = path.split("/")[2];
      const task = await api.task(id);
      const paint = async () => {
        const fresh = await api.task(id);
        root.innerHTML = taskView(fresh, me?.role === "owner");
        bindNav(root);
        const files = root.querySelector("#files") as HTMLInputElement | null;
        files?.addEventListener("change", () => {
          const names = [...(files.files || [])].map((f) => f.name).join(", ");
          const picked = root.querySelector("#picked");
          if (picked) picked.textContent = names || "";
        });
        root.querySelector("#upload")?.addEventListener("click", async () => {
          const note = (root.querySelector("#note") as HTMLTextAreaElement).value;
          const list = [...(files?.files || [])];
          try {
            await api.uploadEvidence(id, note, list);
            haptic("success");
            await paint();
          } catch (e) {
            error = (e as Error).message;
            await paint();
          }
        });
        root.querySelector("#close")?.addEventListener("click", async () => {
          try {
            await api.closeTask(id);
            haptic("success");
            go(`/goals/${task.goal_id}`);
          } catch (e) {
            error = (e as Error).message;
            await paint();
          }
        });
        root.querySelector("#reject")?.addEventListener("click", async () => {
          const reason = prompt("Чому відхиляєте? Виконавець побачить причину.") || "";
          if (!reason.trim()) return;
          try {
            await api.rejectTask(id, reason);
            haptic("error");
            go(`/goals/${task.goal_id}`);
          } catch (e) {
            error = (e as Error).message;
            await paint();
          }
        });
      };
      await paint();
    } else if (path === "/join") {
      root.innerHTML = joinView();
      root.querySelector("#save")?.addEventListener("click", async () => {
        const code = (root.querySelector("#code") as HTMLInputElement).value;
        try {
          const res = await api.redeem(code);
          haptic("success");
          go(`/goals/${res.goal_id}`);
        } catch (e) {
          error = (e as Error).message;
          root.innerHTML = joinView();
          bindNav(root);
        }
      });
    } else {
      go("/");
    }
    bindNav(root);
  } catch (e) {
    if ((e as Error).message.includes("повторний")) {
      clearToken();
      me = null;
    }
    root.innerHTML = `<div class="err">${esc((e as Error).message)}</div><button class="btn" data-go="#/">На головну</button>`;
    bindNav(root);
  }
}

bootTelegram();
window.addEventListener("hashchange", () => {
  void render();
});
void render();
