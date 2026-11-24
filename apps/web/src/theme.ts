export type ThemeChoice = "dark" | "light" | "system";
const KEY = "localpilot.theme";

export function getThemeChoice(): ThemeChoice {
  const v = localStorage.getItem(KEY);
  return v === "light" || v === "dark" || v === "system" ? v : "dark";
}

function resolve(choice: ThemeChoice): "dark" | "light" {
  if (choice !== "system") return choice;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function applyTheme(choice: ThemeChoice = getThemeChoice()) {
  document.documentElement.dataset.theme = resolve(choice);
}

export function setThemeChoice(choice: ThemeChoice) {
  localStorage.setItem(KEY, choice);
  applyTheme(choice);
  window.dispatchEvent(new CustomEvent("localpilot-theme", { detail: choice }));
}

window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", () => {
  if (getThemeChoice() === "system") applyTheme("system");
});
