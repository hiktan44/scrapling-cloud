import Script from "next/script";
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
      <link rel="stylesheet" href="/site-visit-preference-v1.css" />
        <Script src="/site-visit-preference-v1.js" strategy="afterInteractive" referrerPolicy="no-referrer" data-site-origin="https://scrape.seymata.com" data-local-session-keys="scrapling_cloud_api_key" />
      </body>
    </html>
  );
}
