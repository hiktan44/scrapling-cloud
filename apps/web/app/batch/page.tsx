"use client";

import {
  BookOpenText,
  CheckCircle2,
  Clock3,
  DatabaseZap,
  Download,
  FileSpreadsheet,
  FileUp,
  Gauge,
  Home,
  Layers3,
  Link2,
  Loader2,
  Play,
  RotateCcw,
  Sparkles,
  UploadCloud,
  XCircle
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type IntelItem = {
  url: string;
  status: string;
  socials: Record<string, string>;
  analysis: string;
  error: string | null;
};

type IntelResult = {
  items?: IntelItem[];
  total?: number;
  succeeded?: number;
};

type JobDetail = {
  id: string;
  status: string;
  kind: string;
  credits: number;
  url: string | null;
  result?: IntelResult | null;
  error?: string | null;
};

type ProgressTone = "active" | "success" | "error";

const socialLabels: Array<{ key: string; label: string }> = [
  { key: "instagram", label: "IG" },
  { key: "facebook", label: "FB" },
  { key: "x", label: "X" },
  { key: "linkedin", label: "IN" },
  { key: "youtube", label: "YT" },
  { key: "tiktok", label: "TT" },
  { key: "whatsapp", label: "WA" },
  { key: "telegram", label: "TG" },
  { key: "pinterest", label: "PT" },
  { key: "github", label: "GH" }
];

export default function BatchPage() {
  const [apiKey, setApiKey] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [job, setJob] = useState<JobDetail | null>(null);
  const [progress, setProgress] = useState({
    visible: false,
    percent: 0,
    status: "ready",
    message: "Hazır",
    tone: "active" as ProgressTone
  });
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const stored = localStorage.getItem("scrapling_cloud_api_key");
    if (!stored) {
      window.location.href = "/login";
      return;
    }
    setApiKey(stored);
  }, []);

  async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${apiUrl}${path}`, {
      ...init,
      headers: { Authorization: `Bearer ${apiKey}`, ...init?.headers }
    });
    const text = await response.text();
    let data: { detail?: unknown } & Record<string, unknown> = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = {};
    }
    if (!response.ok) {
      const detail = typeof data?.detail === "string" ? data.detail : null;
      throw new Error(detail ?? `API isteği başarısız oldu (HTTP ${response.status}). Birkaç saniye sonra tekrar dene.`);
    }
    return data as T;
  }

  function pickFile(candidate: File | null) {
    setError("");
    if (!candidate) {
      return;
    }
    const name = candidate.name.toLowerCase();
    if (!name.endsWith(".xlsx") && !name.endsWith(".csv") && !name.endsWith(".txt")) {
      setError("Desteklenen formatlar: .xlsx, .csv veya .txt");
      return;
    }
    if (candidate.size > 25 * 1024 * 1024) {
      setError("Dosya çok büyük (maksimum 25 MB).");
      return;
    }
    setFile(candidate);
  }

  async function upload() {
    if (!file) {
      setError("Önce bir dosya seç veya sürükle.");
      return;
    }
    setWorking(true);
    setError("");
    setJob(null);
    setProgress({ visible: true, percent: 8, status: "uploading", message: "Dosya yükleniyor", tone: "active" });
    try {
      const form = new FormData();
      form.append("file", file);
      const created = await apiFetch<{ job_id: string; url_count: number; status: string; credits: number }>("/v1/intel/upload", {
        method: "POST",
        body: form
      });
      setProgress({
        visible: true,
        percent: 20,
        status: "queued",
        message: `${created.url_count} site için analiz kuyruğa alındı (${created.credits} kredi)`,
        tone: "active"
      });
      await pollJob(created.job_id, created.url_count);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Dosya yüklenemedi";
      setError(message);
      setProgress({ visible: true, percent: 100, status: "failed", message, tone: "error" });
    } finally {
      setWorking(false);
    }
  }

  async function pollJob(jobId: string, urlCount: number) {
    for (let attempt = 0; attempt < 600; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 4000));
      const detail = await apiFetch<JobDetail>(`/v1/jobs/${jobId}`);
      setJob(detail);
      const status = String(detail.status);
      const percent = Math.min(92, 24 + attempt * 2);
      setProgress({
        visible: true,
        percent: status === "succeeded" || status === "failed" ? 100 : percent,
        status,
        message:
          status === "succeeded"
            ? `Tamamlandı — ${detail.result?.succeeded ?? 0}/${detail.result?.total ?? urlCount} site analiz edildi`
            : status === "failed"
              ? "Job hata aldı, detay için job listesine bak"
              : status === "running"
                ? "Siteler ziyaret ediliyor, sosyal medya ve firma analizi çıkarılıyor"
                : "Kuyrukta, worker bekleniyor",
        tone: status === "succeeded" ? "success" : status === "failed" ? "error" : "active"
      });
      if (!["queued", "running"].includes(status)) {
        return;
      }
    }
    setProgress({
      visible: true,
      percent: 95,
      status: "still-running",
      message: "Analiz sürüyor; biraz sonra sayfayı yenileyip job durumunu kontrol edebilirsin",
      tone: "active"
    });
  }

  async function downloadExcel() {
    if (!job) {
      return;
    }
    setError("");
    try {
      const response = await fetch(`${apiUrl}/v1/intel/${job.id}/export`, {
        headers: { Authorization: `Bearer ${apiKey}` }
      });
      if (!response.ok) {
        throw new Error(`Excel indirilemedi (HTTP ${response.status})`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "firma-analiz-sonuclari.xlsx";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Excel indirilemedi");
    }
  }

  function reset() {
    setJob(null);
    setFile(null);
    setError("");
    setProgress({ visible: false, percent: 0, status: "ready", message: "Hazır", tone: "active" });
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  const items = job?.result?.items ?? [];
  const succeeded = job?.status === "succeeded";

  return (
    <main className="playgroundShell">
      <header className="playgroundTopbar">
        <Link className="logo" href="/dashboard">
          <span>SC</span>
          Scrapling Cloud
        </Link>
        <nav>
          <Link href="/dashboard"><Home size={18} /> Dashboard</Link>
          <Link href="/playground"><Play size={18} /> Playground</Link>
          <Link href="/data"><DatabaseZap size={18} /> Data Explorer</Link>
          <a href={`${apiUrl}/docs`} target="_blank"><BookOpenText size={18} /> API Docs</a>
        </nav>
      </header>

      <section className="playgroundHero">
        <div>
          <h1>Toplu Firma Analizi</h1>
          <p>Excel, CSV veya TXT listeni yükle; her site ziyaret edilip sosyal medya hesapları ve kısa firma analizi çıkarılsın, sonucu Excel olarak indir.</p>
        </div>
        <div className="playgroundPulse">
          <Sparkles size={22} />
          <span>{progress.visible ? progress.message : "Dosya yüklemeye hazır"}</span>
        </div>
      </section>

      <section className="playgroundWorkspace">
        <aside className="requestStudio">
          <div className="studioSection">
            <label className="fieldLabel">Site listesi dosyası</label>
            <div
              className={`dropZone${dragging ? " active" : ""}`}
              onClick={() => inputRef.current?.click()}
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => {
                event.preventDefault();
                setDragging(false);
                pickFile(event.dataTransfer.files?.[0] ?? null);
              }}
            >
              <UploadCloud size={30} />
              <strong>Dosyayı buraya sürükle veya seç</strong>
              <span>.xlsx, .csv veya .txt · maks 25 MB · 1000 siteye kadar</span>
              <input
                ref={inputRef}
                type="file"
                accept=".xlsx,.csv,.txt"
                onChange={(event) => pickFile(event.target.files?.[0] ?? null)}
              />
            </div>
            {file && (
              <div className="fileChip">
                <FileSpreadsheet size={18} />
                <span>{file.name}</span>
                <em>{(file.size / 1024).toFixed(0)} KB</em>
              </div>
            )}
          </div>

          <div className="studioSection">
            <div className="studioHeading">
              <strong>Neler çıkarılır?</strong>
            </div>
            <ul className="intelHints">
              <li><Link2 size={16} /> Instagram, Facebook, X, LinkedIn, YouTube, TikTok ve daha fazlası</li>
              <li><Sparkles size={16} /> Her firma için 2-3 cümlelik Türkçe ürün/hizmet analizi</li>
              <li><FileSpreadsheet size={16} /> Tüm sonuçları içeren indirilebilir Excel raporu</li>
            </ul>
          </div>

          <div className="studioActions">
            <button className="primary" onClick={upload} disabled={working || !file}>
              {working ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
              Analizi başlat
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
            <StatusTile icon={Layers3} title="Site" value={job?.result?.total ? String(job.result.total) : "0"} />
          </div>

          {progress.visible && (
            <div className={`progressCard largeProgress ${progress.tone}`} role="status" aria-live="polite">
              <div className="progressMeta">
                <strong>{progress.message}</strong>
                <span>{progress.status} · {progress.percent}%</span>
              </div>
              <div className="progressTrack" aria-label="Batch progress">
                <i style={{ width: `${progress.percent}%` }} />
              </div>
            </div>
          )}

          {error && <div className="formError">{error}</div>}

          {succeeded && (
            <div className="resultSummary">
              <CheckCircle2 size={20} />
              <div>
                <strong>{job?.result?.succeeded ?? 0}/{job?.result?.total ?? 0} site başarıyla analiz edildi</strong>
                <p>Sosyal medya hesapları ve firma analizleri aşağıda; tamamını Excel olarak indirebilirsin.</p>
              </div>
              <button className="primary" onClick={downloadExcel}>
                <Download size={18} />
                Excel indir
              </button>
            </div>
          )}

          {items.length > 0 && (
            <div className="intelTableWrap">
              <table className="intelTable">
                <thead>
                  <tr>
                    <th>Site</th>
                    <th>Durum</th>
                    <th>Sosyal medya</th>
                    <th>Firma analizi</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.url}>
                      <td>
                        <a href={item.url} target="_blank" rel="noreferrer">
                          {item.url.replace(/^https?:\/\//, "")}
                        </a>
                      </td>
                      <td>
                        {item.status === "ok" ? (
                          <span className="intelStatus ok"><CheckCircle2 size={15} /> OK</span>
                        ) : (
                          <span className="intelStatus err" title={item.error ?? ""}><XCircle size={15} /> Hata</span>
                        )}
                      </td>
                      <td className="socialCell">
                        {Object.keys(item.socials ?? {}).length === 0 && <span className="muted">—</span>}
                        {socialLabels
                          .filter((social) => item.socials?.[social.key])
                          .map((social) => (
                            <a
                              key={social.key}
                              className="socialBadge"
                              href={item.socials[social.key]}
                              target="_blank"
                              rel="noreferrer"
                              title={item.socials[social.key]}
                            >
                              {social.label}
                            </a>
                          ))}
                      </td>
                      <td className="analysisCell">{item.analysis || item.error || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {items.length === 0 && !job && (
            <div className="emptyState">
              <FileUp size={28} />
              <p>Soldan bir dosya yükle; sonuçlar burada listelenecek ve Excel olarak indirilebilecek.</p>
            </div>
          )}
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
