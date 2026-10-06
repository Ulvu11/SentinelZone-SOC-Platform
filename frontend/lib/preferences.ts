"use client";
import { useSyncExternalStore } from "react";
const defaults = JSON.stringify({
  workspace: "Unified SOC",
  density: "comfortable",
  highlightAlerts: true,
});
const subscribe = (callback: () => void) => {
  window.addEventListener("soc-preferences", callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener("soc-preferences", callback);
    window.removeEventListener("storage", callback);
  };
};
const snapshot = () => {
  try {
    return localStorage.getItem("soc-preferences") ?? defaults;
  } catch {
    return defaults;
  }
};
export interface Preferences {
  workspace: string;
  density: "compact" | "comfortable";
  highlightAlerts: boolean;
}
export function usePreferences() {
  const raw = useSyncExternalStore(subscribe, snapshot, () => defaults);
  let preferences: Preferences = JSON.parse(defaults);
  try {
    const saved: Partial<Preferences> = JSON.parse(raw);
    preferences = {
      workspace:
        typeof saved.workspace === "string" ? saved.workspace : "Unified SOC",
      density: saved.density === "compact" ? "compact" : "comfortable",
      highlightAlerts:
        typeof saved.highlightAlerts === "boolean"
          ? saved.highlightAlerts
          : true,
    };
  } catch {}
  const save = (update: Partial<Preferences>) => {
    localStorage.setItem(
      "soc-preferences",
      JSON.stringify({ ...preferences, ...update }),
    );
    window.dispatchEvent(new Event("soc-preferences"));
  };
  return { preferences, save };
}
