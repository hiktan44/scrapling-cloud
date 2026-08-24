"use client";

import { useLang, type Lang } from "../lib/use-lang";

interface LangSwitchProps {
  className?: string;
  ariaLabel?: string;
}

export default function LangSwitch({ className = "", ariaLabel = "Language selector" }: LangSwitchProps) {
  const [lang, setLang] = useLang();

  return (
    <div className={`languageSwitch ${className}`} aria-label={ariaLabel}>
      <button 
        className={lang === "tr" ? "selected" : ""} 
        onClick={() => setLang("tr")}
        aria-label="Switch to Turkish"
        aria-pressed={lang === "tr"}
      >
        TR
      </button>
      <button 
        className={lang === "en" ? "selected" : ""} 
        onClick={() => setLang("en")}
        aria-label="Switch to English"
        aria-pressed={lang === "en"}
      >
        EN
      </button>
    </div>
  );
}