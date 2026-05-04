"use client";

import {
  Activity,
  ArrowRight,
  BookOpenText,
  Copy,
  ExternalLink,
  KeyRound,
  Loader2,
  LogOut,
  Plus,
  RefreshCw,
  Trash2
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Usage = {
  plan: string;
  monthly_credits: number;
  used_credits: number;
  remaining_credits: number;
  concurrency_limit: number;
};

type ApiKey = {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  revoked: boolean;
  last_used_at: string | null;
  created_at: string;
  key?: string | null;
};

type Job = {
  id: string;
  status: string;
  kind: string;
  credits: number;
  url: string | null;
};

type ProgressState = {
  visible: boolean;
  percent: number;
  status: string;
  message: string;
  tone: "active" | "success" | "error";
};

export default function DashboardPage() {
  const [apiKey, setApiKey] = useState("");
  const [workspace, setWorkspace] = useState("Workspace");
  const [usage, setUsage] = useState<Usage | null>(null);
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [newKey, setNewKey] = useState("");
  const [sampleUrl, setSampleUrl] = useState("https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home");
  const [playgroundResult, setPlaygroundResult] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [progress, setProgress] = useState<ProgressState>({
    visible: false,
    percent: 0,
    status: "idle",
    message: "Hazır",
    tone: "active"
  });

  const headers = useMemo(() => ({ Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" }), [apiKey]);

  useEffect(() => {
    const stored = localStorage.getItem("scrapling_cloud_api_key");
    const storedWorkspace = localStorage.getItem("scrapling_cloud_workspace");
    if (!stored) {
      window.location.href = "/login";
      return;
    }
    setApiKey(stored);
    if (storedWorkspace) {
      setWorkspace(storedWorkspace);
    }
  }, []);

  useEffect(() => {
    if (apiKey) {
      void refresh();
    }
  }, [apiKey]);

  async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${apiUrl}${path}`, { ...init, headers: { ...headers, ...init?.headers } });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail ?? "API isteği başarısız oldu");
    }
    return data;
  }

  async function refresh() {
    setError("");
    setLoading(true);
    try {
      const [usageData, keyData, jobData] = await Promise.all([
        apiFetch<Usage>("/v1/usage"),
        apiFetch<ApiKey[]>("/v1/api-keys"),
        apiFetch<Job[]>("/v1/jobs")
      ]);
      setUsage(usageData);
      setKeys(keyData);
      setJobs(jobData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Dashboard yüklenemedi");
      if (err instanceof Error && err.message.toLowerCase().includes("invalid")) {
        localStorage.removeItem("scrapling_cloud_api_key");
      }
    } finally {
      setLoading(false);
    }
  }

  async function createKey() {
    setWorking(true);
    setError("");
    try {
      const key = await apiFetch<ApiKey>("/v1/api-keys", {
        method: "POST",
        body: JSON.stringify({ name: "Production key" })
      });
      setNewKey(key.key ?? "");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Key oluşturulamadı");
    } finally {
      setWorking(false);
    }
  }

  async function revokeKey(id: string) {
    setWorking(true);
    setError("");
    try {
      await apiFetch(`/v1/api-keys/${id}`, { method: "DELETE" });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Key iptal edilemedi");
    } finally {
      setWorking(false);
    }
  }

  async function runScrape() {
    setWorking(true);
    setError("");
    setPlaygroundResult("");
    setProgress({
      visible: true,
      percent: 8,
      status: "preparing",
      message: "URL hazırlanıyor",
      tone: "active"
    });
    try {
      const normalizedUrl = normalizeUrl(sampleUrl);
      setSampleUrl(normalizedUrl);
      setProgress({
        visible: true,
        percent: 18,
        status: "sending",
        message: "Scrape job API'ye gönderiliyor",
        tone: "active"
      });
      const result = await apiFetch("/v1/scrape", {
        method: "POST",
        body: JSON.stringify({ url: normalizedUrl, formats: ["markdown", "links", "metadata"], mode: "auto" })
      });
      setPlaygroundResult(JSON.stringify(result, null, 2));
      setProgress({
        visible: true,
        percent: 32,
        status: "queued",
        message: "Job kuyruğa alındı, worker bekleniyor",
        tone: "active"
      });
      if (typeof result === "object" && result && "id" in result) {
        await pollJob(String((result as Job).id));
      }
      await refresh();
    } catch (err) {
      setProgress({
        visible: true,
        percent: 100,
        status: "failed",
        message: err instanceof Error ? err.message : "Scrape job gönderilemedi",
        tone: "error"
      });
      setError(err instanceof Error ? err.message : "Scrape job gönderilemedi");
    } finally {
      setWorking(false);
    }
  }

  async function pollJob(jobId: string) {
    for (let attempt = 0; attempt < 8; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 1800));
      const job = await apiFetch<Job & { result?: unknown; error?: string | null }>(`/v1/jobs/${jobId}`);
      setPlaygroundResult(JSON.stringify(job, null, 2));
      const status = String(job.status);
      const percent = Math.min(88, 38 + attempt * 7);
      setProgress({
        visible: true,
        percent: status === "succeeded" ? 100 : status === "failed" ? 100 : percent,
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
      percent: 92,
      status: "still-running",
      message: "Job hala çalışıyor; Son işler bölümünden takip edebilirsin",
      tone: "active"
    });
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
      return "Job hata aldı, detay aşağıdaki sonuçta";
    }
    return "Job durumu güncellendi";
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

  function logout() {
    localStorage.removeItem("scrapling_cloud_api_key");
    localStorage.removeItem("scrapling_cloud_workspace");
    window.location.href = "/login";
  }

  return (
    <main className="dashboardShell">
      <aside className="dashboardSidebar">
        <Link className="logo" href="/">
          <span>SC</span>
          Scrapling Cloud
        </Link>
        <nav>
          <a href="#overview"><Activity size={18} /> Genel bakış</a>
          <a href="#keys"><KeyRound size={18} /> API key</a>
          <a href="#playground"><ArrowRight size={18} /> Playground</a>
          <a href={`${apiUrl}/docs`} target="_blank"><BookOpenText size={18} /> Docs</a>
        </nav>
      </aside>
      <section className="dashboardMain">
        <header className="dashboardTop">
          <div>
            <span>Dashboard</span>
            <h1>{workspace}</h1>
          </div>
          <div className="dashboardActions">
            <button className="secondary" onClick={refresh} disabled={loading}>
              <RefreshCw size={18} />
              Yenile
            </button>
            <button className="secondary" onClick={logout}>
              <LogOut size={18} />
              Çıkış
            </button>
          </div>
        </header>

        {error && <div className="formError dashboardError">{error}</div>}
        {loading && <div className="loadingLine"><Loader2 className="spin" size={18} /> Dashboard yükleniyor</div>}

        <section className="dashboardGrid" id="overview">
          <Metric title="Plan" value={usage?.plan ?? "-"} />
          <Metric title="Kalan kredi" value={usage ? usage.remaining_credits.toLocaleString("tr-TR") : "-"} />
          <Metric title="Kullanılan kredi" value={usage ? usage.used_credits.toLocaleString("tr-TR") : "-"} />
          <Metric title="Concurrency" value={usage ? String(usage.concurrency_limit) : "-"} />
        </section>

        <section className="dashboardPanel" id="keys">
          <div className="panelHeader">
            <div>
              <h2>API key yönetimi</h2>
              <p>Uygulamalarında Bearer token olarak kullanacağın key’leri buradan oluştur.</p>
            </div>
            <button className="primary" onClick={createKey} disabled={working}>
              <Plus size={18} />
              Yeni key
            </button>
          </div>
          {newKey && (
            <div className="newKeyBox">
              <strong>Yeni key, sadece şimdi gösterilir</strong>
              <code>{newKey}</code>
              <button onClick={() => navigator.clipboard.writeText(newKey)}>
                <Copy size={16} />
                Kopyala
              </button>
            </div>
          )}
          <div className="tableList">
            {keys.map((key) => (
              <article key={key.id}>
                <div>
                  <strong>{key.name}</strong>
                  <span>{key.prefix}... · {key.revoked ? "iptal edildi" : "aktif"}</span>
                </div>
                <button onClick={() => revokeKey(key.id)} disabled={working || key.revoked}>
                  <Trash2 size={16} />
                  İptal
                </button>
              </article>
            ))}
          </div>
        </section>

        <section className="dashboardPanel playgroundPanel" id="playground">
          <div className="panelHeader">
            <div>
              <h2>Scrape playground</h2>
              <p>Bir URL gönder, API kuyruğa bir scrape job eklesin.</p>
            </div>
            <a className="secondary" href={`${apiUrl}/docs`} target="_blank">
              Docs
              <ExternalLink size={18} />
            </a>
          </div>
          <div className="playgroundControls">
            <input
              value={sampleUrl}
              onChange={(event) => setSampleUrl(event.target.value)}
              onFocus={(event) => event.currentTarget.select()}
              placeholder="https://example.com"
            />
            <button className="primary" onClick={runScrape} disabled={working}>
              {working ? <Loader2 className="spin" size={18} /> : <ArrowRight size={18} />}
              Job gönder
            </button>
          </div>
          {progress.visible && (
            <div className={`progressCard ${progress.tone}`} role="status" aria-live="polite">
              <div className="progressMeta">
                <strong>{progress.message}</strong>
                <span>{progress.status} · {progress.percent}%</span>
              </div>
              <div className="progressTrack" aria-label="Scrape progress">
                <i style={{ width: `${progress.percent}%` }} />
              </div>
            </div>
          )}
          <pre>{playgroundResult || "Sonuç burada görünecek."}</pre>
        </section>

        <section className="dashboardPanel">
          <div className="panelHeader">
            <div>
              <h2>Son işler</h2>
              <p>API üzerinden oluşturulan son scrape, crawl, map ve extract job’ları.</p>
            </div>
          </div>
          <div className="tableList">
            {jobs.length === 0 && <p className="emptyState">Henüz job yok.</p>}
            {jobs.map((job) => (
              <article key={job.id}>
                <div>
                  <strong>{job.kind} · {job.status}</strong>
                  <span>{job.url ?? job.id}</span>
                </div>
                <span>{job.credits} kredi</span>
              </article>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

function Metric({ title, value }: { title: string; value: string }) {
  return (
    <article className="dashboardMetric">
      <span>{title}</span>
      <strong>{value}</strong>
    </article>
  );
}
