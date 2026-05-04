"use client";

import {
  ArrowRight,
  BookOpenText,
  Check,
  Clock3,
  Code2,
  Copy,
  DatabaseZap,
  Gauge,
  Globe2,
  Home,
  Layers3,
  Loader2,
  Play,
  RefreshCw,
  RotateCcw,
  Sparkles
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Format = "markdown" | "html" | "text" | "links" | "metadata";
type Mode = "auto" | "static" | "dynamic" | "stealth";
type ProgressTone = "active" | "success" | "error";

type JobResponse = {
  id: string;
  status: string;
  kind: string;
  credits: number;
  url: string | null;
  result?: Record<string, unknown> | null;
  error?: string | null;
};

const formatOptions: Array<{ value: Format; label: string }> = [
  { value: "markdown", label: "Markdown" },
  { value: "links", label: "Links" },
  { value: "metadata", label: "Metadata" },
  { value: "text", label: "Text" },
  { value: "html", label: "HTML" }
];

const modeOptions: Array<{ value: Mode; label: string; text: string }> = [
  { value: "auto", label: "Auto", text: "Domain profiline göre seç" },
  { value: "static", label: "Static", text: "Hızlı HTTP fetch" },
  { value: "dynamic", label: "Dynamic", text: "Browser render" },
  { value: "stealth", label: "Stealth", text: "Zorlu sayfalar" }
];

export default function PlaygroundPage() {
  const [apiKey, setApiKey] = useState("");
  const [url, setUrl] = useState("https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home");
  const [formats, setFormats] = useState<Format[]>(["markdown", "links", "metadata"]);
  const [mode, setMode] = useState<Mode>("auto");
  const [waitFor, setWaitFor] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [job, setJob] = useState<JobResponse | null>(null);
  const [resultText, setResultText] = useState("Henüz job gönderilmedi.");
  const [progress, setProgress] = useState({
    visible: false,
    percent: 0,
    status: "ready",
    message: "Hazır",
    tone: "active" as ProgressTone
  });

  const headers = useMemo(() => ({ Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" }), [apiKey]);

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

  function toggleFormat(format: Format) {
    setFormats((current) => {
      if (current.includes(format)) {
        return current.length === 1 ? current : current.filter((item) => item !== format);
      }
      return [...current, format];
    });
  }

  async function runScrape() {
    setWorking(true);
    setError("");
    setJob(null);
    setResultText("");
    setProgress({
      visible: true,
      percent: 8,
      status: "preparing",
      message: "URL ve request hazırlanıyor",
      tone: "active"
    });

    try {
      const normalizedUrl = normalizeUrl(url);
      setUrl(normalizedUrl);
      setProgress({
        visible: true,
        percent: 20,
        status: "sending",
        message: "Scrape job API'ye gönderiliyor",
        tone: "active"
      });

      const created = await apiFetch<JobResponse>("/v1/scrape", {
        method: "POST",
        body: JSON.stringify({
          url: normalizedUrl,
          formats,
          mode,
          wait_for: waitFor.trim() || null
        })
      });
      setJob(created);
      setResultText(JSON.stringify(created, null, 2));
      setProgress({
        visible: true,
        percent: 34,
        status: "queued",
        message: "Job kuyruğa alındı, worker bekleniyor",
        tone: "active"
      });
      await pollJob(created.id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Scrape job gönderilemedi";
      setError(message);
      setProgress({
        visible: true,
        percent: 100,
        status: "failed",
        message,
        tone: "error"
      });
    } finally {
      setWorking(false);
    }
  }

  async function pollJob(jobId: string) {
    for (let attempt = 0; attempt < 10; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 1600));
      const detail = await apiFetch<JobResponse>(`/v1/jobs/${jobId}`);
      setJob(detail);
      setResultText(JSON.stringify(detail, null, 2));
      const status = String(detail.status);
      const percent = Math.min(90, 40 + attempt * 6);
      setProgress({
        visible: true,
        percent: status === "succeeded" || status === "failed" ? 100 : percent,
        status,
        message: progressMessage(status, attempt),
        tone: status === "succeeded" ? "success" : status === "failed" ? "error" : "active"
      });
      if (!["queued", "running"].includes(status)) {
        return;
      }
    }
    setProgress({
      visible: true,
      percent: 94,
      status: "still-running",
      message: "Job hala çalışıyor; biraz sonra yenileyebilirsin",
      tone: "active"
    });
  }

  function reset() {
    setJob(null);
    setError("");
    setResultText("Henüz job gönderilmedi.");
    setProgress({ visible: false, percent: 0, status: "ready", message: "Hazır", tone: "active" });
  }

  const metadata = job?.result && typeof job.result === "object" ? job.result.metadata as { title?: string; description?: string } | undefined : undefined;

  return (
    <main className="playgroundShell">
      <header className="playgroundTopbar">
        <Link className="logo" href="/dashboard">
          <span>SC</span>
          Scrapling Cloud
        </Link>
        <nav>
          <Link href="/dashboard"><Home size={18} /> Dashboard</Link>
          <a href={`${apiUrl}/docs`} target="_blank"><BookOpenText size={18} /> API Docs</a>
        </nav>
      </header>

      <section className="playgroundHero">
        <div>
          <h1>Scrape Playground</h1>
          <p>URL gönder, formatları seç, worker durumunu canlı izle ve dönen veriyi tek ekranda incele.</p>
        </div>
        <div className="playgroundPulse">
          <Sparkles size={22} />
          <span>{progress.visible ? progress.message : "Canlı API testi hazır"}</span>
        </div>
      </section>

      <section className="playgroundWorkspace">
        <aside className="requestStudio">
          <div className="studioSection">
            <label className="fieldLabel">Hedef URL</label>
            <div className="urlInput">
              <Globe2 size={20} />
              <input value={url} onChange={(event) => setUrl(event.target.value)} onFocus={(event) => event.currentTarget.select()} />
            </div>
          </div>

          <div className="studioSection">
            <div className="studioHeading">
              <strong>Formatlar</strong>
              <span>{formats.length} seçili</span>
            </div>
            <div className="formatGrid">
              {formatOptions.map((item) => (
                <button
                  className={formats.includes(item.value) ? "selected" : ""}
                  key={item.value}
                  onClick={() => toggleFormat(item.value)}
                >
                  <Check size={16} />
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          <div className="studioSection">
            <div className="studioHeading">
              <strong>Render modu</strong>
              <span>{mode}</span>
            </div>
            <div className="modeGrid">
              {modeOptions.map((item) => (
                <button className={mode === item.value ? "selected" : ""} key={item.value} onClick={() => setMode(item.value)}>
                  <strong>{item.label}</strong>
                  <span>{item.text}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="studioSection">
            <label className="fieldLabel">Wait selector</label>
            <input
              className="plainInput"
              value={waitFor}
              onChange={(event) => setWaitFor(event.target.value)}
              placeholder=".content-ready veya boş bırak"
            />
          </div>

          <div className="studioActions">
            <button className="primary" onClick={runScrape} disabled={working}>
              {working ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
              Çalıştır
            </button>
            <button className="secondary" onClick={reset} disabled={working}>
              <RotateCcw size={18} />
              Temizle
            </button>
          </div>
        </aside>

        <section className="liveConsole">
          <div className="statusStrip">
            <StatusTile icon={Clock3} title="Durum" value={job?.status ?? progress.status} />
            <StatusTile icon={Gauge} title="Kredi" value={job ? String(job.credits) : "0"} />
            <StatusTile icon={Layers3} title="Format" value={formats.join(", ")} />
          </div>

          {progress.visible && (
            <div className={`progressCard largeProgress ${progress.tone}`} role="status" aria-live="polite">
              <div className="progressMeta">
                <strong>{progress.message}</strong>
                <span>{progress.status} · {progress.percent}%</span>
              </div>
              <div className="progressTrack" aria-label="Scrape progress">
                <i style={{ width: `${progress.percent}%` }} />
              </div>
            </div>
          )}

          {metadata && (
            <div className="resultSummary">
              <DatabaseZap size={20} />
              <div>
                <strong>{metadata.title ?? "Metadata alındı"}</strong>
                <p>{metadata.description ?? "Sonuç içinde metadata, link ve markdown alanları hazır."}</p>
              </div>
            </div>
          )}

          {error && <div className="formError">{error}</div>}

          <div className="consoleHeader">
            <span><Code2 size={18} /> Response</span>
            <button onClick={() => navigator.clipboard.writeText(resultText)}>
              <Copy size={16} />
              Kopyala
            </button>
          </div>
          <pre>{resultText}</pre>
        </section>
      </section>
    </main>
  );
}

function StatusTile({ icon: Icon, title, value }: { icon: typeof Clock3; title: string; value: string }) {
  return (
    <article className="statusTile">
      <Icon size={18} />
      <span>{title}</span>
      <strong>{value}</strong>
    </article>
  );
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

function progressMessage(status: string, attempt: number) {
  if (status === "queued") {
    return "Kuyrukta, worker sıraya alıyor";
  }
  if (status === "running") {
    return attempt < 3 ? "Sayfa çekiliyor ve içerik ayrıştırılıyor" : "Sonuç hazırlanıyor";
  }
  if (status === "succeeded") {
    return "Tamamlandı, sonuç hazır";
  }
  if (status === "failed") {
    return "Job hata aldı, detay response alanında";
  }
  return "Job durumu güncellendi";
}
