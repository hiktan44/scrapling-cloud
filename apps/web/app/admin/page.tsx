"use client";

import {
  ArrowRight,
  BookOpenText,
  Copy,
  CreditCard,
  DatabaseZap,
  Home,
  KeyRound,
  Loader2,
  RefreshCw,
  ShieldCheck,
  WalletCards
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useT } from "../../lib/i18n";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type AdminOrganization = {
  id: string;
  name: string;
  plan: string;
  monthly_credits: number;
  used_credits: number;
  remaining_credits: number;
  concurrency_limit: number;
  owner_email: string | null;
  created_at: string;
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

export default function AdminPage() {
  const t = useT();
  const [apiKey, setApiKey] = useState("");
  const [organizations, setOrganizations] = useState<AdminOrganization[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [credits, setCredits] = useState(10000);
  const [plan, setPlan] = useState("");
  const [concurrency, setConcurrency] = useState(5);
  const [keyName, setKeyName] = useState("Customer production key");
  const [newKey, setNewKey] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);

  const headers = useMemo(() => ({ Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" }), [apiKey]);
  const selected = organizations.find((org) => org.id === selectedId) ?? organizations[0] ?? null;

  useEffect(() => {
    const stored = localStorage.getItem("scrapling_cloud_api_key");
    if (!stored) {
      window.location.href = "/login";
      return;
    }
    setApiKey(stored);
  }, []);

  useEffect(() => {
    if (apiKey) {
      void refresh();
    }
  }, [apiKey]);

  useEffect(() => {
    if (selected) {
      setSelectedId(selected.id);
      setPlan(selected.plan);
      setConcurrency(selected.concurrency_limit);
    }
  }, [selected?.id]);

  async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${apiUrl}${path}`, { ...init, headers: { ...headers, ...init?.headers } });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail ?? t("admin.adminRequestFailed"));
    }
    return data;
  }

  async function refresh() {
    setError("");
    setLoading(true);
    try {
      const data = await apiFetch<AdminOrganization[]>("/v1/admin/organizations");
      setOrganizations(data);
      if (!selectedId && data[0]) {
        setSelectedId(data[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t("admin.adminLoadError"));
    } finally {
      setLoading(false);
    }
  }

  async function updateCredits(operation: "add" | "set_monthly" | "reset_usage") {
    if (!selected) {
      return;
    }
    setWorking(true);
    setError("");
    setMessage("");
    try {
      const updated = await apiFetch<AdminOrganization>(`/v1/admin/organizations/${selected.id}/credits`, {
        method: "POST",
        body: JSON.stringify({
          operation,
          credits,
          plan: plan.trim() || null,
          concurrency_limit: concurrency
        })
      });
      setOrganizations((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setMessage(operation === "add" ? t("admin.creditsLoaded") : operation === "set_monthly" ? t("admin.monthlyLimitUpdated") : t("admin.usageReset"));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("admin.creditsUpdateError"));
    } finally {
      setWorking(false);
    }
  }

  async function createCustomerKey() {
    if (!selected) {
      return;
    }
    setWorking(true);
    setError("");
    setMessage("");
    setNewKey("");
    try {
      const key = await apiFetch<ApiKey>(`/v1/admin/organizations/${selected.id}/api-keys`, {
        method: "POST",
        body: JSON.stringify({ name: keyName, scopes: ["scrape", "crawl", "map", "extract"] })
      });
      setNewKey(key.key ?? "");
      setMessage(`${selected.name} ${t("admin.forWorkspace")} ${t("admin.apiKeyCreated")}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("admin.apiKeyCreateError"));
    } finally {
      setWorking(false);
    }
  }

  return (
    <main className="dashboardShell adminShell">
      <aside className="dashboardSidebar">
        <Link className="logo" href="/dashboard"><span>SC</span> Scrapling Cloud</Link>
        <nav>
          <Link href="/dashboard"><Home size={18} /> {t("dashboard.dashboard")}</Link>
          <a href="#organizations"><ShieldCheck size={18} /> {t("admin.organizations")}</a>
          <a href="#credits"><WalletCards size={18} /> {t("admin.creditManagement")}</a>
          <a href="#keys"><KeyRound size={18} /> {t("admin.userKeys")}</a>
          <Link href="/data"><DatabaseZap size={18} /> {t("dashboard.dataExplorer")}</Link>
          <a href={`${apiUrl}/docs`} target="_blank"><BookOpenText size={18} /> {t("dashboard.docs")}</a>
        </nav>
      </aside>

      <section className="dashboardMain">
        <header className="dashboardTop">
          <div>
            <span>{t("admin.admin")}</span>
            <h1>{t("admin.userAndCreditManagement")}</h1>
          </div>
          <div className="dashboardActions">
            <button className="secondary" onClick={refresh} disabled={loading}>
              <RefreshCw size={18} />
              {t("common.refresh")}
            </button>
          </div>
        </header>

        {error && <div className="formError dashboardError">{error}</div>}
        {message && <div className="successNotice">{message}</div>}
        {loading && <div className="loadingLine"><Loader2 className="spin" size={18} /> {t("admin.adminDataLoading")}</div>}

        <section className="dashboardGrid">
          <Metric title={t("admin.workspace")} value={String(organizations.length)} />
          <Metric title={t("admin.totalCredits")} value={organizations.reduce((sum, org) => sum + org.monthly_credits, 0).toLocaleString("tr-TR")} />
          <Metric title={t("admin.used")} value={organizations.reduce((sum, org) => sum + org.used_credits, 0).toLocaleString("tr-TR")} />
          <Metric title={t("admin.selectedRemaining")} value={selected ? selected.remaining_credits.toLocaleString("tr-TR") : "-"} />
        </section>

        <section className="dashboardPanel" id="organizations">
          <div className="panelHeader">
            <div>
              <h2>{t("admin.allUsers")}</h2>
              <p>{t("admin.allUsersDesc")}</p>
            </div>
          </div>
          <div className="adminOrgGrid">
            {organizations.map((org) => (
              <button className={selectedId === org.id ? "selected" : ""} key={org.id} onClick={() => setSelectedId(org.id)}>
                <span>{org.owner_email ?? t("admin.noEmail")}</span>
                <strong>{org.name}</strong>
                <small>{org.plan} · {org.remaining_credits.toLocaleString("tr-TR")} {t("admin.remainingCredits")}</small>
              </button>
            ))}
          </div>
        </section>

        <section className="dashboardPanel adminControlGrid" id="credits">
          <div>
            <h2>{t("admin.addCredits")}</h2>
            <p>{selected ? `${selected.name} ${t("admin.forWorkspace")} ${t("admin.addCreditsDesc")}` : t("admin.selectWorkspace")}</p>
          </div>
          <div className="adminFormGrid">
            <label>
              {t("admin.credits")}
              <input type="number" min={0} value={credits} onChange={(event) => setCredits(Number(event.target.value))} />
            </label>
            <label>
              {t("admin.plan")}
              <input value={plan} onChange={(event) => setPlan(event.target.value)} />
            </label>
            <label>
              {t("admin.concurrency")}
              <input type="number" min={1} max={1000} value={concurrency} onChange={(event) => setConcurrency(Number(event.target.value))} />
            </label>
          </div>
          <div className="adminButtonRow">
            <button className="primary" onClick={() => updateCredits("add")} disabled={working || !selected}>
              <CreditCard size={18} />
              {t("admin.addCredit")}
            </button>
            <button className="secondary" onClick={() => updateCredits("set_monthly")} disabled={working || !selected}>
              {t("admin.setMonthlyLimit")}
            </button>
            <button className="secondary" onClick={() => updateCredits("reset_usage")} disabled={working || !selected}>
              {t("admin.resetUsage")}
            </button>
          </div>
        </section>

        <section className="dashboardPanel adminControlGrid" id="keys">
          <div>
            <h2>{t("admin.generateApiKey")}</h2>
            <p>{t("admin.generateApiKeyDesc")}</p>
          </div>
          <div className="adminFormGrid single">
            <label>
              {t("admin.keyName")}
              <input value={keyName} onChange={(event) => setKeyName(event.target.value)} />
            </label>
          </div>
          <div className="adminButtonRow">
            <button className="primary" onClick={createCustomerKey} disabled={working || !selected}>
              <KeyRound size={18} />
              {t("admin.createApiKey")}
              <ArrowRight size={18} />
            </button>
          </div>
          {newKey && (
            <div className="newKeyBox">
              <strong>{t("admin.newUserApiKey")}</strong>
              <code>{newKey}</code>
              <button onClick={() => navigator.clipboard.writeText(newKey)}>
                <Copy size={16} />
                {t("common.copy")}
              </button>
            </div>
          )}
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
