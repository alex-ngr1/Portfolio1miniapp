export type TgUser = {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
};

type WebApp = {
  initData: string;
  initDataUnsafe: { user?: TgUser };
  ready: () => void;
  expand: () => void;
  colorScheme: "light" | "dark";
  themeParams: Record<string, string>;
  HapticFeedback?: {
    impactOccurred: (style: "light" | "medium" | "heavy") => void;
    notificationOccurred: (type: "error" | "success" | "warning") => void;
  };
  BackButton: {
    show: () => void;
    hide: () => void;
    onClick: (cb: () => void) => void;
    offClick: (cb: () => void) => void;
  };
  MainButton: {
    setText: (t: string) => void;
    show: () => void;
    hide: () => void;
    onClick: (cb: () => void) => void;
    offClick: (cb: () => void) => void;
  };
};

declare global {
  interface Window {
    Telegram?: { WebApp?: WebApp };
  }
}

export const tg = window.Telegram?.WebApp;

export function bootTelegram(): void {
  tg?.ready();
  tg?.expand();
}

export function haptic(kind: "light" | "success" | "error" = "light"): void {
  if (kind === "light") tg?.HapticFeedback?.impactOccurred("light");
  if (kind === "success") tg?.HapticFeedback?.notificationOccurred("success");
  if (kind === "error") tg?.HapticFeedback?.notificationOccurred("error");
}

export function hasTelegramUser(): boolean {
  return Boolean(tg?.initData && tg.initDataUnsafe.user);
}
