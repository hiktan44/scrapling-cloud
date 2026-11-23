"use client";

import { useLang, type Lang } from "../lib/use-lang";

interface LangSwitchProps {
  className?: string;
  ariaLabel?: string;
}

export default function LangSwitch({ className = "", ariaLabel = "Dil seçimi" }: LangSwitchProps) {
  const [lang, setLang] = useLang();

  return (
    <div className={`languageSwitch ${className}`} aria-label={ariaLabel}>
      <button 
        className={lang === "tr" ? "selected" : ""} 
        onClick={() => setLang("tr")}
        aria-label="Türkçeye geç"
        aria-pressed={lang === "tr"}
      >
        TR
      </button>
      <button 
        className={lang === "en" ? "selected" : ""} 
        onClick={() => setLang("en")}
        aria-label="İngilizceye geç"
        aria-pressed={lang === "en"}
      >
        EN
      </button>
    </div>
  );
}
