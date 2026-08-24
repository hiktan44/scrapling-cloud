import type { Metadata } from "next";
import "./styles.css";
import LangProvider from "../components/LangProvider";

export const metadata: Metadata = {
  title: "Scrapling Cloud",
  description: "Self-hosted scraping API platform powered by Scrapling"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <body>
        <LangProvider>{children}</LangProvider>
      </body>
    </html>
  );
}
