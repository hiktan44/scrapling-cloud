"use client";

import { useLang } from "../lib/use-lang";
import { useEffect } from "react";

interface LangProviderProps {
  children: React.ReactNode;
}

export default function LangProvider({ children }: LangProviderProps) {
  const [lang] = useLang();

  useEffect(() => {
    // Update HTML lang attribute for accessibility and SEO
    document.documentElement.lang = lang;
  }, [lang]);

  return <>{children}</>;
}