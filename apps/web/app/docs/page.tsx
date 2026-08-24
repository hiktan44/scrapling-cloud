"use client";

import { ArrowLeft, Terminal } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { useT } from "../../lib/i18n";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Endpoint = {
  method: string;
  path: string;
  summary: string;
  body?: string;
  note?: string;
};

type Section = {
  id: string;
  title: string;
  blurb: string;
  endpoints: Endpoint[];
};

const SECTIONS: Section[] = [
  {
    id: "auth",
    title: "Kimlik doğrulama",
    blurb:
      "Tüm /v1 uç noktaları Bearer API anahtarı ister. Anahtarı Dashboard'dan alın ve Authorization başlığında gönderin.",
    endpoints: [
      { method: "POST", path: "/v1/auth/signup", summary: "Hesap + organizasyon + ilk API anahtarı oluştur", body: '{ "email": "you@firma.com", "password": "en-az-8", "organization_name": "Firmam" }' },
      { method: "POST", path: "/v1/auth/login", summary: "Giriş yap, panel API anahtarı al", body: '{ "email": "you@firma.com", "password": "..." }' },
      { method: "GET", path: "/v1/me", summary: "Geçerli hesabı döndür" },
      { method: "GET", path: "/v1/usage", summary: "Plan, kredi ve eşzamanlılık limiti" }
    ]
  },
  {
    id: "scrape",
    title: "Scrape",
    blurb:
      "Tek bir sayfayı istediğiniz formatlarda çekin. Async iş döner; /v1/jobs/{id} ile sonucu alın veya SSE ile canlı izleyin.",
    endpoints: [
      {
        method: "POST",
        path: "/v1/scrape",
        summary: "Formats: markdown, html, raw_html, text, links, images, metadata, screenshot, summary, json",
        body: '{ "url": "https://example.com", "formats": ["markdown","screenshot"], "mode": "auto", "only_main_content": true, "change_tracking": false, "max_age": 0 }',
        note: "mode: auto | static | dynamic | stealth. screenshot_full_page, include_tags, exclude_tags, headers, mobile, timeout, proxy da desteklenir."
      }
    ]
  },
  {
    id: "crawl",
    title: "Crawl",
    blurb: "Bir siteyi aynı alan adı içinde gezin; sayfa ve derinlik limitleri, regex filtreleri, robots.txt saygısı.",
    endpoints: [
      {
        method: "POST",
        path: "/v1/crawl",
        summary: "Site geneli gezinme + isteğe bağlı AI analizi",
        body: '{ "url": "https://site.com", "limit": 50, "max_depth": 2, "include": ["/blog/"], "exclude": ["/tag/"], "allow_subdomains": false, "respect_robots": true, "delay": 0 }'
      }
    ]
  },
  {
    id: "map",
    title: "Map",
    blurb: "Hızlı URL keşfi: robots.txt + sitemap.xml + sayfa linkleri. Tam scrape yapmaz, sadece URL listeler.",
    endpoints: [
      {
        method: "POST",
        path: "/v1/map",
        summary: "URL keşfi (senkron)",
        body: '{ "url": "https://site.com", "limit": 250, "include_subdomains": false, "sitemap": "include", "search": "opsiyonel filtre" }'
      }
    ]
  },
  {
    id: "extract",
    title: "Extract",
    blurb: "Bir veya çok sayıda URL'den yapılandırılmış veri çıkarın. site.com/* joker adresi map ile genişletilir.",
    endpoints: [
      {
        method: "POST",
        path: "/v1/extract",
        summary: "Şema ve/veya prompt ile LLM çıkarımı",
        body: '{ "urls": ["https://site.com", "https://site.com/blog/*"], "prompt": "Başlık ve tarihleri çıkar", "schema": { "type": "object", "properties": { "articles": { "type": "array" } } } }'
      }
    ]
  },
  {
    id: "search",
    title: "Search",
    blurb: "Web araması (self-host SearXNG). Sonuçları isteğe bağlı olarak scrape edip markdown ekleyebilir.",
    endpoints: [
      {
        method: "POST",
        path: "/v1/search",
        summary: "Web araması + opsiyonel sonuç scrape",
        body: '{ "query": "Horizon Europe calls 2026", "limit": 10, "scrape_formats": ["markdown"], "time_range": "month" }'
      }
    ]
  },
  {
    id: "batch",
    title: "Batch & Intel",
    blurb: "Çok sayıda URL'yi paralel işleyin; Intel akışı Excel/CSV yükleyip sosyal medya + firma analizini çıkarır.",
    endpoints: [
      { method: "POST", path: "/v1/batch", summary: "URL listesini paralel scrape et", body: '{ "urls": ["https://a.com","https://b.com"], "formats": ["markdown"], "max_concurrency": 5 }' },
      { method: "POST", path: "/v1/intel/upload", summary: "Excel/CSV/TXT yükle → toplu firma istihbaratı (multipart)" },
      { method: "GET", path: "/v1/intel/{job_id}/export", summary: "Biçimli .xlsx indir" }
    ]
  },
  {
    id: "parse",
    title: "Parse",
    blurb: "Yerel bir dosyayı (PDF/DOCX/XLSX/HTML/TXT/CSV/MD) markdown'a çevirin. Ağ isteği yok.",
    endpoints: [{ method: "POST", path: "/v1/parse", summary: "Dosya → markdown (multipart, ≤25MB)" }]
  },
  {
    id: "monitors",
    title: "Monitors",
    blurb: "Bir sayfayı zamanlanmış olarak izleyin; değişince (isteğe bağlı AI 'anlamlı değişiklik' yargısıyla) webhook bildirimi alın.",
    endpoints: [
      { method: "POST", path: "/v1/monitors", summary: "İzleyici oluştur", body: '{ "name": "EU çağrıları", "url": "https://ec.europa.eu/...", "interval_minutes": 60, "judge_enabled": true, "goal": "Yeni fon çağrısı", "webhook_url": "https://firma.com/hook", "notify_on": "meaningful" }' },
      { method: "GET", path: "/v1/monitors", summary: "İzleyicileri listele" },
      { method: "GET", path: "/v1/monitors/{id}", summary: "İzleyici + son 20 kontrol" },
      { method: "POST", path: "/v1/monitors/{id}/run", summary: "Şimdi çalıştır" },
      { method: "DELETE", path: "/v1/monitors/{id}", summary: "İzleyiciyi sil" }
    ]
  },
  {
    id: "billing",
    title: "Faturalama",
    blurb: "Planlar ve Stripe self-servis abonelik. Webhook aboneliği plan/kredi değişimlerini işler.",
    endpoints: [
      { method: "GET", path: "/v1/billing/plans", summary: "Plan kataloğu (starter/growth/scale)" },
      { method: "POST", path: "/v1/billing/checkout", summary: "Stripe ödeme oturumu başlat", body: '{ "plan": "growth", "success_url": "https://.../ok", "cancel_url": "https://.../iptal" }' },
      { method: "POST", path: "/v1/billing/portal", summary: "Müşteri portalı oturumu", body: '{ "return_url": "https://.../hesap" }' }
    ]
  }
];

const TOOLS = [
  { name: "Python SDK", detail: "pip install scrapling-cloud-sdk", code: 'from scrapling_cloud_sdk import ScraplingCloud\nclient = ScraplingCloud(api_key="sk_...")\npage = client.scrape("https://example.com", formats=["markdown"])\nprint(page["markdown"])' },
  { name: "MCP server", detail: "Claude / Cursor / VS Code için", code: 'SCRAPLING_API_KEY=sk_... \\\n  python -m scrapling_cloud.mcp_server' }
];

const methodColor: Record<string, string> = {
  GET: "var(--blue)",
  POST: "var(--teal)",
  DELETE: "var(--coral)",
  PATCH: "var(--amber)"
};

export default function DocsPage() {
  const t = useT();
  const [active, setActive] = useState("auth");
  const curl = useMemo(
    () =>
      `curl -X POST ${apiUrl}/v1/scrape \\\n  -H "Authorization: Bearer sk_..." \\\n  -H "Content-Type: application/json" \\\n  -d '{"url":"https://example.com","formats":["markdown"]}'`,
    []
  );

  return (
    <main style={{ maxWidth: 1080, margin: "0 auto", padding: "32px 24px 80px" }}>
      <Link href="/" style={{ display: "inline-flex", gap: 8, alignItems: "center", color: "var(--muted)", textDecoration: "none", fontSize: 14 }}>
        <ArrowLeft size={16} /> {t("common.back")} {t("home.footerProduct")}
      </Link>

      <header style={{ marginTop: 24, marginBottom: 32 }}>
        <h1 style={{ fontSize: 40, margin: "0 0 8px", letterSpacing: -1 }}>API {t("nav.docs")}</h1>
        <p style={{ color: "var(--muted)", fontSize: 17, maxWidth: 720 }}>
          Scrapling Cloud, temiz web verisi gereken ürünler için scrape / crawl / map / extract / search / monitor API'sidir.
          Taban URL: <code style={{ background: "var(--soft)", padding: "2px 6px", borderRadius: 6 }}>{apiUrl}</code>
        </p>
      </header>

      <section style={{ background: "var(--ink)", color: "#e9f2f0", borderRadius: 14, padding: 20, marginBottom: 36 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center", color: "#9fd9d0", fontSize: 13, marginBottom: 10 }}>
          <Terminal size={15} /> Hızlı başlangıç
        </div>
        <pre style={{ margin: 0, fontSize: 13, lineHeight: 1.6, whiteSpace: "pre-wrap", fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}>{curl}</pre>
      </section>

      <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 32, alignItems: "start" }}>
        <nav style={{ position: "sticky", top: 24, display: "flex", flexDirection: "column", gap: 4 }}>
          {SECTIONS.map((section) => (
            <a
              key={section.id}
              href={`#${section.id}`}
              onClick={() => setActive(section.id)}
              style={{
                padding: "8px 12px",
                borderRadius: 8,
                textDecoration: "none",
                fontSize: 14,
                color: active === section.id ? "var(--teal-dark)" : "var(--muted)",
                background: active === section.id ? "var(--soft)" : "transparent",
                fontWeight: active === section.id ? 600 : 500
              }}
            >
              {section.title}
            </a>
          ))}
          <a href="#tools" onClick={() => setActive("tools")} style={{ padding: "8px 12px", borderRadius: 8, textDecoration: "none", fontSize: 14, color: "var(--muted)", fontWeight: 500 }}>
            SDK & MCP
          </a>
        </nav>

        <div style={{ minWidth: 0 }}>
          {SECTIONS.map((section) => (
            <section key={section.id} id={section.id} style={{ marginBottom: 44, scrollMarginTop: 24 }}>
              <h2 style={{ fontSize: 24, margin: "0 0 6px" }}>{section.title}</h2>
              <p style={{ color: "var(--muted)", margin: "0 0 16px", fontSize: 15 }}>{section.blurb}</p>
              {section.endpoints.map((ep) => (
                <div key={ep.path + ep.method} style={{ border: "1px solid var(--line)", borderRadius: 12, padding: 16, marginBottom: 12 }}>
                  <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                    <span style={{ background: methodColor[ep.method] ?? "var(--muted)", color: "#fff", fontSize: 12, fontWeight: 700, padding: "3px 8px", borderRadius: 6 }}>{ep.method}</span>
                    <code style={{ fontSize: 15, fontWeight: 600 }}>{ep.path}</code>
                  </div>
                  <p style={{ margin: "10px 0 0", fontSize: 14, color: "var(--ink)" }}>{ep.summary}</p>
                  {ep.body && (
                    <pre style={{ marginTop: 12, marginBottom: 0, background: "var(--soft)", padding: 12, borderRadius: 8, fontSize: 12.5, overflowX: "auto", fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}>{ep.body}</pre>
                  )}
                  {ep.note && <p style={{ margin: "10px 0 0", fontSize: 13, color: "var(--muted)" }}>{ep.note}</p>}
                </div>
              ))}
            </section>
          ))}

          <section id="tools" style={{ marginBottom: 20, scrollMarginTop: 24 }}>
            <h2 style={{ fontSize: 24, margin: "0 0 6px" }}>SDK & MCP</h2>
            <p style={{ color: "var(--muted)", margin: "0 0 16px", fontSize: 15 }}>Resmi Python istemcisi ve MCP server ile kod içinden veya AI istemcilerinden erişin.</p>
            {TOOLS.map((tool) => (
              <div key={tool.name} style={{ border: "1px solid var(--line)", borderRadius: 12, padding: 16, marginBottom: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12, flexWrap: "wrap" }}>
                  <strong style={{ fontSize: 16 }}>{tool.name}</strong>
                  <span style={{ color: "var(--muted)", fontSize: 13 }}>{tool.detail}</span>
                </div>
                <pre style={{ marginTop: 12, marginBottom: 0, background: "var(--soft)", padding: 12, borderRadius: 8, fontSize: 12.5, overflowX: "auto", fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}>{tool.code}</pre>
              </div>
            ))}
          </section>
        </div>
      </div>
    </main>
  );
}
