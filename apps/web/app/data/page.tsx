"use client";

import {
  ArrowRight,
  BookOpenText,
  DatabaseZap,
  FileText,
  Gauge,
  Globe2,
  Home,
  Layers3,
  Link as LinkIcon,
  Loader2,
  Map,
  Play,
  RefreshCw,
  Search,
  Sparkles
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Mode = "auto" | "static" | "dynamic" | "stealth";
type Tone = "active" | "success" | "error";

type CrawlPage = {
  url: string;
  depth: number;
  title?: string | null;
  description?: string | null;
  markdown?: string | null;
  text?: string | null;
  links?: string[];
};

type AiAnalysis = {
  enabled?: boolean;
  provider?: string;
  reason?: string;
  prompt?: string | null;
  summary?: string;
  key_points?: string[];
  opportunities?: Array<string | Record<string, unknown>>;
  entities?: Array<string | Record<string, unknown>>;
  recommended_actions?: string[];
  page_summaries?: Array<{ title?: string; url?: string; summary?: string; important_items?: string[] }>;
};

type CrawlResult = {
  url: string;
  max_depth: number;
  limit: number;
  pages_scraped: number;
  links_discovered: number;
  ai?: AiAnalysis | null;
  pages: CrawlPage[];
  discovered: string[];
  errors: Array<{ url: string; error: string }>;
};

type JobDetail = {
  id: string;
  status: string;
  kind: string;
  credits: number;
  url: string | null;
  result?: CrawlResult | null;
  error?: string | null;
};

export default function DataExplorerPage() {
  const [apiKey, setApiKey] = useState("");
  const [url, setUrl] = useState("https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home");
  const [limit, setLimit] = useState(12);
  const [maxDepth, setMaxDepth] = useState(2);
  const [mode, setMode] = useState<Mode>("static");
  const [analysisPrompt, setAnalysisPrompt] = useState(
    "Bu sitedeki verileri kullanarak kullanıcının işine yarayacak anlamlı bir rapor çıkar. Önemli başlıkları, fırsat/ihale sinyallerini, kurumları, tarihleri ve yapılacak aksiyonları Türkçe listele."
  );
  const [query, setQuery] = useState("");
  const [job, setJob] = useState<JobDetail | null>(null);
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);
  const [progress, setProgress] = useState({ visible: false, percent: 0, status: "ready", message: "Hazır", tone: "active" as Tone });

  const headers = useMemo(() => ({ Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" }), [apiKey]);
  const result = job?.result ?? null;
  const ai = result?.ai ?? null;
  const pages = useMemo(() => {
    const all = result?.pages ?? [];
    const needle = query.trim().toLowerCase();
    if (!needle) {
      return all;
    }
    return all.filter((page) => [page.url, page.title, page.description, page.markdown, page.text].some((value) => String(value ?? "").toLowerCase().includes(needle)));
  }, [query, result]);

  useEffect(() => {
    const stored = localStorage.getItem("scrapling_cloud_api_key");
    if (!stored) {
      window.location.href = "/login";
      return;
    }
    setApiKey(stored);
  }, []);

  async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${apiUrl}${path}`, { ...init, headers: { ...headers, ...init?.headers } });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail ?? "API isteği başarısız oldu");
    }
    return data;
  }

  async function runCrawl() {
    setWorking(true);
    setError("");
    setJob(null);
    setProgress({ visible: true, percent: 8, status: "preparing", message: "Crawl isteği hazırlanıyor", tone: "active" });
    try {
      const normalizedUrl = normalizeUrl(url);
      setUrl(normalizedUrl);
      setProgress({ visible: true, percent: 18, status: "sending", message: "Derin crawl job API'ye gönderiliyor", tone: "active" });
      const created = await apiFetch<JobDetail>("/v1/crawl", {
        method: "POST",
        body: JSON.stringify({
          url: normalizedUrl,
          limit,
          max_depth: maxDepth,
          mode,
          ai_extract: true,
          analysis_prompt: analysisPrompt.trim() || null,
          formats: ["markdown", "links", "metadata", "text"]
        })
      });
      setJob(created);
      setProgress({ visible: true, percent: 32, status: "queued", message: "Job kuyruğa alındı, sayfalar keşfedilecek", tone: "active" });
      await pollJob(created.id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Crawl başlatılamadı";
      setError(message);
      setProgress({ visible: true, percent: 100, status: "failed", message, tone: "error" });
    } finally {
      setWorking(false);
    }
  }

  async function pollJob(jobId: string) {
    for (let attempt = 0; attempt < 18; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 1800));
      const detail = await apiFetch<JobDetail>(`/v1/jobs/${jobId}`);
      setJob(detail);
      const status = String(detail.status);
      const percent = Math.min(92, 38 + attempt * 4);
      setProgress({
        visible: true,
        percent: status === "succeeded" || status === "failed" ? 100 : percent,
        status,
        message: crawlMessage(status, attempt),
        tone: status === "succeeded" ? "success" : status === "failed" ? "error" : "active"
      });
      if (!["queued", "running"].includes(status)) {
        return;
      }
    }
    setProgress({ visible: true, percent: 94, status: "still-running", message: "Crawl hala çalışıyor; biraz sonra tekrar kontrol et", tone: "active" });
  }

  return (
    <main className="dataShell">
      <header className="playgroundTopbar">
        <Link className="logo" href="/dashboard"><span>SC</span> Scrapling Cloud</Link>
        <nav>
          <Link href="/dashboard"><Home size={18} /> Dashboard</Link>
          <Link href="/playground"><Sparkles size={18} /> Playground</Link>
          <a href={`${apiUrl}/docs`} target="_blank"><BookOpenText size={18} /> API Docs</a>
        </nav>
      </header>

      <section className="dataHero">
        <div>
          <h1>Data Explorer</h1>
          <p>Bir başlangıç URL’sinden derinlere in, aynı domain içindeki sayfaları scrape et ve çıkan yazıları okunabilir bir veri panosunda gör.</p>
        </div>
        <div className="dataHeroCard">
          <Map size={24} />
          <strong>{result ? `${result.pages_scraped} sayfa scrape edildi` : "Derin crawl hazır"}</strong>
          <span>{result ? `${result.links_discovered} link keşfedildi` : "Depth ve limit seç, başlat"}</span>
        </div>
      </section>

      <section className="dataWorkspace">
        <aside className="crawlControls">
          <label>
            Başlangıç URL
            <span className="urlInput">
              <Globe2 size={20} />
              <input value={url} onChange={(event) => setUrl(event.target.value)} onFocus={(event) => event.currentTarget.select()} />
            </span>
          </label>
          <div className="numberGrid">
            <label>
              Sayfa limiti
              <input type="number" min={1} max={100} value={limit} onChange={(event) => setLimit(Number(event.target.value))} />
            </label>
            <label>
              Derinlik
              <input type="number" min={0} max={5} value={maxDepth} onChange={(event) => setMaxDepth(Number(event.target.value))} />
            </label>
          </div>
          <div className="studioSection">
            <div className="studioHeading">
              <strong>Mod</strong>
              <span>{mode}</span>
            </div>
            <div className="modeGrid">
              {(["static", "auto", "dynamic", "stealth"] as Mode[]).map((item) => (
                <button className={mode === item ? "selected" : ""} key={item} onClick={() => setMode(item)}>
                  <strong>{item}</strong>
                  <span>{item === "static" ? "Hızlı crawl" : item === "auto" ? "Profil destekli" : item === "dynamic" ? "Browser render" : "Stealth render"}</span>
                </button>
              ))}
            </div>
          </div>
          <label>
            Analiz prompt'u
            <textarea
              className="promptInput"
              value={analysisPrompt}
              onChange={(event) => setAnalysisPrompt(event.target.value)}
              placeholder="Örn: Bu sitedeki fon çağrılarını sektör, bütçe, son başvuru tarihi ve uygunluk kriterlerine göre çıkar."
            />
          </label>
          <button className="primary crawlButton" onClick={runCrawl} disabled={working}>
            {working ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
            Derin crawl başlat
          </button>
          {error && <div className="formError">{error}</div>}
        </aside>

        <section className="dataResults">
          <div className="statusStrip">
            <StatusTile icon={Gauge} title="Durum" value={job?.status ?? progress.status} />
            <StatusTile icon={FileText} title="Sayfa" value={String(result?.pages_scraped ?? 0)} />
            <StatusTile icon={LinkIcon} title="Link" value={String(result?.links_discovered ?? 0)} />
            <StatusTile icon={DatabaseZap} title="Kredi" value={String(job?.credits ?? 0)} />
          </div>

          {progress.visible && (
            <div className={`progressCard largeProgress ${progress.tone}`} role="status" aria-live="polite">
              <div className="progressMeta">
                <strong>{progress.message}</strong>
                <span>{progress.status} · {progress.percent}%</span>
              </div>
              <div className="progressTrack" aria-label="Crawl progress">
                <i style={{ width: `${progress.percent}%` }} />
              </div>
            </div>
          )}

          {ai && (
            <section className={ai.enabled ? "aiSummary" : "aiSummary fallback"}>
              <div className="aiSummaryHead">
                <div>
                  <span>AI Summary</span>
                  <h2>{ai.enabled ? "LLM analizi hazır" : "LLM fallback özeti"}</h2>
                </div>
                <strong>{ai.provider ?? "analysis"}</strong>
              </div>
              <p>{ai.summary}</p>
              {ai.prompt && (
                <div className="promptEcho">
                  <strong>Kullanılan prompt</strong>
                  <span>{ai.prompt}</span>
                </div>
              )}
              {ai.reason && <small>{ai.reason}</small>}
              <div className="aiGrid">
                <AiList title="Önemli noktalar" items={ai.key_points} />
                <AiList title="Önerilen aksiyonlar" items={ai.recommended_actions} />
              </div>
              {ai.opportunities && ai.opportunities.length > 0 && (
                <div className="aiBlock">
                  <strong>Fırsatlar / ihale sinyalleri</strong>
                  <ul>
                    {ai.opportunities.slice(0, 8).map((item, index) => <li key={index}>{formatAiItem(item)}</li>)}
                  </ul>
                </div>
              )}
              {ai.page_summaries && ai.page_summaries.length > 0 && (
                <div className="aiPages">
                  {ai.page_summaries.slice(0, 8).map((page, index) => (
                    <article key={`${page.url}-${index}`}>
                      <strong>{page.title || "Sayfa özeti"}</strong>
                      <p>{page.summary}</p>
                      {page.url && <a href={page.url} target="_blank">{page.url}</a>}
                    </article>
                  ))}
                </div>
              )}
            </section>
          )}

          <div className="dataToolbar">
            <div className="searchBox">
              <Search size={18} />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Başlık, URL veya metinde ara" />
            </div>
            <button className="secondary" onClick={() => job && void pollJob(job.id)} disabled={!job || working}>
              <RefreshCw size={18} />
              Yenile
            </button>
          </div>

          <div className="pageList">
            {!result && <div className="emptyData">Henüz veri yok. Soldan bir crawl başlatınca sayfalar burada listelenir.</div>}
            {pages.map((page) => (
              <article className="pageResult" key={page.url}>
                <div className="pageResultTop">
                  <span>Depth {page.depth}</span>
                  <a href={page.url} target="_blank">{page.url}</a>
                </div>
                <h2>{page.title || "Başlıksız sayfa"}</h2>
                {page.description && <p>{page.description}</p>}
                <pre>{trimText(page.markdown || page.text || "Bu sayfadan gösterilecek metin alınamadı.")}</pre>
                <div className="pageMeta">
                  <span>{page.links?.length ?? 0} link</span>
                  <span>{(page.markdown || page.text || "").length.toLocaleString("tr-TR")} karakter</span>
                </div>
              </article>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

function StatusTile({ icon: Icon, title, value }: { icon: typeof Gauge; title: string; value: string }) {
  return (
    <article className="statusTile">
      <Icon size={18} />
      <span>{title}</span>
      <strong>{value}</strong>
    </article>
  );
}

function AiList({ title, items }: { title: string; items?: string[] }) {
  if (!items || items.length === 0) {
    return null;
  }
  return (
    <div className="aiBlock">
      <strong>{title}</strong>
      <ul>
        {items.slice(0, 8).map((item) => <li key={item}>{item}</li>)}
      </ul>
    </div>
  );
}

function formatAiItem(item: string | Record<string, unknown>) {
  if (typeof item === "string") {
    return item;
  }
  return Object.entries(item).map(([key, value]) => `${key}: ${String(value)}`).join(" · ");
}

function trimText(value: string) {
  return value.length > 1600 ? `${value.slice(0, 1600)}\n\n...` : value;
}

function normalizeUrl(value: string) {
  let url = value.trim();
  url = url.replace(/^https\/\//, "https://").replace(/^http\/\//, "http://");
  const embeddedProtocol = url.slice(8).search(/https?:\/\/|https\/\//);
  if (embeddedProtocol >= 0) {
    url = url.slice(8 + embeddedProtocol).replace(/^https\/\//, "https://").replace(/^http\/\//, "http://");
  }
  if (!/^https?:\/\//.test(url)) {
    throw new Error("Lütfen URL'yi https:// ile birlikte gir.");
  }
  try {
    new URL(url);
  } catch {
    throw new Error("URL formatı geçerli değil. Örnek: https://example.com");
  }
  return url;
}

function crawlMessage(status: string, attempt: number) {
  if (status === "queued") {
    return "Kuyrukta, worker crawler'ı başlatacak";
  }
  if (status === "running") {
    return attempt < 5 ? "Sayfalar keşfediliyor ve scrape ediliyor" : "Veriler birleştiriliyor";
  }
  if (status === "succeeded") {
    return "Crawl tamamlandı, veriler hazır";
  }
  if (status === "failed") {
    return "Crawl hata aldı";
  }
  return "Crawl durumu güncellendi";
}
