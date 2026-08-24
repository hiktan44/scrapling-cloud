"use client";

import { ArrowRight, KeyRound, Loader2, LockKeyhole, Mail } from "lucide-react";
import Link from "next/link";
import { FormEvent, useState } from "react";
import { useT } from "../../lib/i18n";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Mode = "login" | "signup";

export default function LoginPage() {
  const t = useT();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [organizationName, setOrganizationName] = useState("My Workspace");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    const endpoint = mode === "login" ? "/v1/auth/login" : "/v1/auth/signup";
    const body =
      mode === "login"
        ? { email, password }
        : { email, password, organization_name: organizationName };

    try {
      const response = await fetch(`${apiUrl}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail ?? t("auth.loginFailed"));
      }
      localStorage.setItem("scrapling_cloud_api_key", data.api_key);
      localStorage.setItem("scrapling_cloud_workspace", data.organization_name);
      localStorage.setItem("scrapling_cloud_is_admin", data.is_admin ? "true" : "false");
      window.location.href = "/dashboard";
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.unexpectedError"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="authShell">
      <section className="authPanel">
        <Link className="logo" href="/">
          <span>SC</span>
          Scrapling Cloud
        </Link>
        <div>
          <h1>{mode === "login" ? t("auth.loginTitle") : t("auth.signupTitle")}</h1>
          <p>
            {t("auth.loginDesc")}
          </p>
        </div>
        <div className="authSwitch">
          <button className={mode === "login" ? "selected" : ""} onClick={() => setMode("login")}>
            {t("auth.loginTab")}
          </button>
          <button className={mode === "signup" ? "selected" : ""} onClick={() => setMode("signup")}>
            {t("auth.signupTab")}
          </button>
        </div>
        <form className="authForm" onSubmit={submit}>
          {mode === "signup" && (
            <label>
              {t("auth.workspaceName")}
              <input value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} />
            </label>
          )}
          <label>
            {t("auth.email")}
            <span>
              <Mail size={18} />
              <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            </span>
          </label>
          <label>
            {t("auth.password")}
            <span>
              <LockKeyhole size={18} />
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                minLength={mode === "signup" ? 8 : 1}
                required
              />
            </span>
          </label>
          {error && <div className="formError">{error}</div>}
          <button className="primary authSubmit" type="submit" disabled={loading}>
            {loading ? <Loader2 className="spin" size={18} /> : <KeyRound size={18} />}
            {mode === "login" ? t("auth.enterDashboard") : t("auth.createAccount")}
            <ArrowRight size={18} />
          </button>
        </form>
      </section>
      <aside className="authAside">
        <div className="authMetric">
          <span>{t("auth.freeCredits")}</span>
          <strong>10,000</strong>
        </div>
        <div className="authMetric">
          <span>{t("auth.endpoint")}</span>
          <strong>/v1/scrape</strong>
        </div>
        <pre>{`curl -X POST ${apiUrl}/v1/scrape \\
  -H "Authorization: Bearer sk_..." \\
  -d ‘{"url":"https://example.com"}’`}</pre>
      </aside>
    </main>
  );
}
