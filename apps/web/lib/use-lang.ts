"use client";

import { useEffect, useState } from "react";

type Lang = "tr" | "en";

const STORAGE_KEY = "ui_lang";
const COOKIE_NAME = "ui_lang";
const CACHE_KEY = "ip_country_cache";
const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours

// IP detection with timeout and caching
async function detectCountry(): Promise<string> {
  // Check session storage cache first
  try {
    const cached = sessionStorage.getItem(CACHE_KEY);
    if (cached) {
      const { country, timestamp } = JSON.parse(cached);
      if (Date.now() - timestamp < CACHE_DURATION) {
        return country;
      }
    }
  } catch {
    // Ignore cache errors
  }

  // Try multiple IP services with fallback
  const services = [
    { url: "https://ipapi.co/json/", timeout: 2500 },
    { url: "https://ipwho.is/", timeout: 2500 }
  ];

  for (const service of services) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), service.timeout);
      
      const response = await fetch(service.url, {
        signal: controller.signal,
        headers: { "Accept": "application/json" }
      });
      
      clearTimeout(timeoutId);
      
      if (response.ok) {
        const data = await response.json();
        const country = data.country_code || data.country?.code || "";
        
        // Cache the result
        try {
          sessionStorage.setItem(CACHE_KEY, JSON.stringify({
            country: country.toUpperCase(),
            timestamp: Date.now()
          }));
        } catch {
          // Ignore cache errors
        }
        
        return country.toUpperCase();
      }
    } catch {
      // Try next service
      continue;
    }
  }

  // Fallback to empty string (will use browser language)
  return "";
}

function getInitialLang(): Lang {
  if (typeof window === "undefined") return "tr";

  // 1. Check localStorage preference (highest priority)
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "tr" || stored === "en") {
      return stored;
    }
  } catch {
    // Ignore localStorage errors
  }

  // 2. Check cookie
  try {
    const cookies = document.cookie.split(";");
    const langCookie = cookies.find(c => c.trim().startsWith(`${COOKIE_NAME}=`));
    if (langCookie) {
      const value = langCookie.split("=")[1]?.trim();
      if (value === "tr" || value === "en") {
        return value;
      }
    }
  } catch {
    // Ignore cookie errors
  }

  // 3. Check browser language
  try {
    const browserLang = navigator.language;
    if (browserLang.toLowerCase().startsWith("tr")) {
      return "tr";
    }
  } catch {
    // Ignore navigator errors
  }

  // 4. Default to Turkish for Turkey
  return "tr";
}

export function useLang(): [Lang, (lang: Lang) => void] {
  const [lang, setLangState] = useState<Lang>(getInitialLang);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);

    // Detect country and update language if no preference exists
    const storedPref = localStorage.getItem(STORAGE_KEY);
    if (!storedPref && !document.cookie.includes(`${COOKIE_NAME}=`)) {
      detectCountry().then((country) => {
        if (country === "TR") {
          setLang("tr");
        } else {
          setLang("en");
        }
      }).catch(() => {
        // Fallback to browser language on error
        const browserLang = navigator.language;
        setLang(browserLang.toLowerCase().startsWith("tr") ? "tr" : "en");
      });
    }
  }, []);

  const setLang = (newLang: Lang) => {
    setLangState(newLang);
    
    // Update localStorage
    try {
      localStorage.setItem(STORAGE_KEY, newLang);
    } catch {
      // Ignore localStorage errors
    }

    // Update cookie (1 year expiry)
    try {
      const date = new Date();
      date.setFullYear(date.getFullYear() + 1);
      document.cookie = `${COOKIE_NAME}=${newLang}; expires=${date.toUTCString()}; path=/; SameSite=Lax`;
    } catch {
      // Ignore cookie errors
    }

    // Dispatch custom event for other components
    try {
      window.dispatchEvent(new CustomEvent("ui_lang_change", { detail: { lang: newLang } }));
    } catch {
      // Ignore event errors
    }
  };

  return [lang, setLang];
}

// Helper function to pick value based on language
export function pickByLang<T>(lang: Lang, tr: T, en: T): T {
  return lang === "tr" ? tr : en;
}

// Export types
export type { Lang };