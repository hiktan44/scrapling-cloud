"use client";

import { useCallback, useEffect, useSyncExternalStore } from "react";

function subscribe(onChange: () => void) {
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

const serverSnapshot = () => undefined;

// Sunucu çıktısı depolanan anahtarı içermez; tarayıcı kendi değerini okur.
export function useStoredValue(key: string): string | null | undefined {
  const read = useCallback(() => {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  }, [key]);
  return useSyncExternalStore(subscribe, read, serverSnapshot);
}

export function useStoredApiKey(): string {
  const key = useStoredValue("scrapling_cloud_api_key");
  useEffect(() => {
    if (key === null || key === "") {
      window.location.href = "/login";
    }
  }, [key]);
  return key ?? "";
}
