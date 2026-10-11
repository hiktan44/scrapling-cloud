"use client";

import { useCallback, useSyncExternalStore } from "react";

export type Lang = "tr" | "en";

const STORAGE_KEY = "ui_lang";
const EVENT_NAME = "ui_lang_change";
let temporaryPreference: Lang | null = null;

function readLanguage(): Lang {
  if (temporaryPreference) return temporaryPreference;
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "tr" || stored === "en") return stored;
  } catch {
    // Depolama kapalıysa çerez tercihine veya Türkçeye dön.
  }
  try {
    const cookie = document.cookie.split(";").find(value => value.trim().startsWith("ui_lang="));
    const value = cookie?.split("=")[1]?.trim();
    if (value === "tr" || value === "en") return value;
  } catch {
    // Çerez kapalıysa varsayılan dil Türkçe.
  }
  return "tr";
}

function subscribe(onChange: () => void) {
  const storageChanged = (event: StorageEvent) => {
    if (event.key === STORAGE_KEY || event.key === null) {
      temporaryPreference = null;
      onChange();
    }
  };
  window.addEventListener("storage", storageChanged);
  window.addEventListener(EVENT_NAME, onChange);
  return () => {
    window.removeEventListener("storage", storageChanged);
    window.removeEventListener(EVENT_NAME, onChange);
  };
}

const serverLanguage = (): Lang => "tr";

export function useLang(): [Lang, (lang: Lang) => void] {
  const lang = useSyncExternalStore(subscribe, readLanguage, serverLanguage);
  const setLang = useCallback((newLang: Lang) => {
    temporaryPreference = newLang;
    try {
      window.localStorage.setItem(STORAGE_KEY, newLang);
    } catch {
      // Çerez tercihinin kaydedilmesi yine denenir.
    }
    try {
      const expires = new Date();
      expires.setFullYear(expires.getFullYear() + 1);
      document.cookie = `ui_lang=${newLang}; expires=${expires.toUTCString()}; path=/; SameSite=Lax`;
    } catch {
      // Kaydetme kapalıysa mevcut tercih okunmaya devam eder.
    }
    window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: { lang: newLang } }));
  }, []);
  return [lang, setLang];
}

export function pickByLang<T>(lang: Lang, tr: T, en: T): T {
  return lang === "tr" ? tr : en;
}
