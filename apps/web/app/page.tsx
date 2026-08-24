"use client";

import {
  ArrowRight,
  BookOpenText,
  Bot,
  Check,
  Code2,
  FileJson2,
  Gauge,
  Globe2,
  KeyRound,
  LineChart,
  LockKeyhole,
  Map,
  Radar,
  ShieldCheck,
  Sparkles,
  Star,
  Webhook
} from "lucide-react";
import { useEffect, useState } from "react";
import { useT } from "../lib/i18n";
import { pickByLang } from "../lib/use-lang";
import LangSwitch from "../components/LangSwitch";

const features = {
  en: [
  {
    title: "Scrape",
    text: "Turn any page into markdown, html, text, links, metadata and screenshots with predictable API responses.",
    icon: Globe2,
    tone: "teal"
  },
  {
    title: "Crawl",
    text: "Run async site crawls with depth, limits, include/exclude rules, live job states and webhook callbacks.",
    icon: Radar,
    tone: "blue"
  },
  {
    title: "Map",
    text: "Discover URLs, sitemaps and link graphs before you spend credits on full extraction workflows.",
    icon: Map,
    tone: "amber"
  },
  {
    title: "Extract",
    text: "Send a schema and receive structured JSON for product pages, docs, articles and internal datasets.",
    icon: FileJson2,
    tone: "green"
  },
  {
    title: "API Keys",
    text: "Create scoped keys, rotate secrets, track last-used activity and separate production from development.",
    icon: KeyRound,
    tone: "coral"
  },
  {
    title: "Safe Learning",
    text: "Learn domain strategies from successful jobs without letting automation rewrite production code.",
    icon: Sparkles,
    tone: "violet"
  }
],
  tr: [
    {
      title: "Scrape",
      text: "Her sayfayı tahmin edilebilir API yanıtlarıyla markdown, html, text, link, metadata ve screenshot formatlarına dönüştürün.",
      icon: Globe2,
      tone: "teal"
    },
    {
      title: "Crawl",
      text: "Depth, limit, include/exclude kuralları, canlı job durumları ve webhook callback’leriyle async site crawl çalıştırın.",
      icon: Radar,
      tone: "blue"
    },
    {
      title: "Map",
      text: "Tam extraction akışına kredi harcamadan önce URL’leri, sitemap’leri ve link graph’larını keşfedin.",
      icon: Map,
      tone: "amber"
    },
    {
      title: "Extract",
      text: "Bir schema gönderin; ürün sayfaları, dokümanlar, makaleler ve veri setleri için structured JSON alın.",
      icon: FileJson2,
      tone: "green"
    },
    {
      title: "API Keys",
      text: "Scoped key oluşturun, secret rotate edin, son kullanım bilgisini görün ve production/development ortamlarını ayırın.",
      icon: KeyRound,
      tone: "coral"
    },
    {
      title: "Güvenli Öğrenme",
      text: "Başarılı job’lardan domain stratejileri öğrenilir; otomasyonun production kodunu yeniden yazmasına izin verilmez.",
      icon: Sparkles,
      tone: "violet"
    }
  ]
} as const;

const testimonials = {
  en: [
  {
    quote: "We moved scraping, crawl jobs and structured extraction behind one API in a week. The domain learning signals made failures much easier to debug.",
    name: "Aylin K.",
    role: "Founder, MarketOps"
  },
  {
    quote: "The credit model is clear enough for product teams and strict enough for infrastructure. It feels built for real SaaS operations.",
    name: "Deniz M.",
    role: "Platform Lead, Atlas AI"
  },
  {
    quote: "Our apps call one endpoint, then receive clean markdown or JSON. The dashboard gives support exactly the job history they need.",
    name: "Selim T.",
    role: "CTO, DataForge"
  }
],
  tr: [
    {
      quote: "Scraping, crawl job’ları ve structured extraction’ı bir haftada tek API arkasına taşıdık. Domain learning sinyalleri hataları çok daha kolay anlaşılır yaptı.",
      name: "Aylin K.",
      role: "Founder, MarketOps"
    },
    {
      quote: "Kredi modeli ürün ekipleri için yeterince net, altyapı için yeterince kontrollü. Gerçek SaaS operasyonu için tasarlanmış gibi.",
      name: "Deniz M.",
      role: "Platform Lead, Atlas AI"
    },
    {
      quote: "Uygulamalarımız tek endpoint çağırıyor, temiz markdown veya JSON alıyor. Dashboard destek ekibine tam gereken job geçmişini veriyor.",
      name: "Selim T.",
      role: "CTO, DataForge"
    }
  ]
} as const;

const pricing = {
  en: [
  ["Starter", "10k", "Small apps and internal tools"],
  ["Growth", "50k", "Production apps and teams"],
  ["Scale", "Custom", "High-volume pipelines"]
],
  tr: [
    ["Starter", "10k", "Küçük uygulamalar ve iç araçlar"],
    ["Growth", "50k", "Production uygulamalar ve ekipler"],
    ["Scale", "Özel", "Yüksek hacimli veri hatları"]
  ]
} as const;

export default function Home() {
  const t = useT();
  const [lang, setLang] = useState<"tr" | "en">("tr");
  const publicApiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const [successRate, setSuccessRate] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${publicApiUrl}/v1/public/stats`)
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (!cancelled && data && typeof data.success_rate === "number") {
          setSuccessRate(data.success_rate);
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [publicApiUrl]);

  return (
    <main>
      <Header apiUrl={publicApiUrl} />
      <section className="hero">
        <div className="heroCopy">
          <h1>{t("home.heroTitle")}</h1>
          <p>
            {t("home.heroText")}
          </p>
          <div className="heroActions">
            <a className="primary" href="#pricing">
              {t("home.primaryCta")}
              <ArrowRight size={18} />
            </a>
            <a className="secondary" href="#api">
              {t("home.docsCta")}
              <BookOpenText size={18} />
            </a>
          </div>
          <div className="trustRow">
            <span><Check size={16} /> {t("home.trust")}</span>
            <span><Check size={16} /> {t("home.trust2")}</span>
            <span><Check size={16} /> {t("home.trust3")}</span>
          </div>
        </div>
        <div className="heroVisual" aria-label="API response and usage preview">
          <div className="codeWindow">
            <div className="windowBar">
              <span />
              <span />
              <span />
              <strong>POST /v1/scrape</strong>
            </div>
            <pre>{`{
  "url": "https://example.com",
  "formats": ["markdown", "links"],
  "mode": "auto"
}

→ 200 ${t("home.queued")}
{
  "id": "job_7H9K",
  "status": "running",
  "credits": 1
}`}</pre>
          </div>
          <div className="chartCard floating">
            <div>
              <span>{t("home.successRateLive")}</span>
              <strong>{successRate !== null ? `${successRate}%` : "—"}</strong>
            </div>
            <MiniChart />
          </div>
        </div>
      </section>

      <section className="featureBand" id="features">
        <div className="sectionHeading">
          <h2>{t("home.featureTitle")}</h2>
          <p>{t("home.featureText")}</p>
        </div>
        <div className="featureGrid">
          {features[lang].map((feature) => (
            <article className={`featureCard ${feature.tone}`} key={feature.title}>
              <div className="featureIcon"><feature.icon size={24} /></div>
              <h3>{feature.title}</h3>
              <p>{feature.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="workflow">
        <div className="sectionHeading">
          <h2>{t("home.workflowTitle")}</h2>
          <p>{t("home.workflowText")}</p>
        </div>
        <div className="steps">
          <Step number="01" title={t("home.step1Title")} text={t("home.step1Text")} icon={LockKeyhole} />
          <Step number="02" title={t("home.step2Title")} text={t("home.step2Text")} icon={Code2} />
          <Step number="03" title={t("home.step3Title")} text={t("home.step3Text")} icon={Bot} />
        </div>
      </section>

      <section className="analytics">
        <div className="analyticsCopy">
          <h2>{t("home.analyticsTitle")}</h2>
          <p>{t("home.analyticsText")}</p>
          <ul>
            <li><Gauge size={18} /> {t("home.analyticsBullet1")}</li>
            <li><Webhook size={18} /> {t("home.analyticsBullet2")}</li>
            <li><ShieldCheck size={18} /> {t("home.analyticsBullet3")}</li>
          </ul>
        </div>
        <div className="analyticsBoard">
          <div className="metricCard tealMetric">
            <span>{t("dashboard.remainingCredits")}</span>
            <strong>49,982</strong>
            <div className="meter"><i /></div>
          </div>
          <div className="metricCard">
            <span>{t("dashboard.active")}</span>
            <strong>12</strong>
            <p>8 concurrent workers</p>
          </div>
          <div className="graphPanel">
            <div className="graphHeader">
              <span>{t("dashboard.weeklyUsage")}</span>
              <LineChart size={18} />
            </div>
            <MiniChart large />
          </div>
        </div>
      </section>

      <section className="apiSection" id="api">
        <div className="apiCopy">
          <h2>{t("home.docsTitle")}</h2>
          <p>{t("home.docsText")}</p>
          <a className="secondary" href="/docs">
            {t("home.openDocs")}
            <ArrowRight size={18} />
          </a>
        </div>
        <div className="docsCard">
          <div className="docTabs">
            <span className="selected">curl</span>
            <span>TypeScript</span>
            <span>Python</span>
          </div>
          <pre>{`curl -X POST ${publicApiUrl}/v1/scrape \\
  -H "Authorization: Bearer sk_..." \\
  -H "Content-Type: application/json" \\
  -d ‘{"url":"https://example.com","formats":["markdown","links"]}’`}</pre>
        </div>
      </section>

      <section className="testimonials" id="customers">
        <div className="sectionHeading">
          <h2>{t("home.testimonialsTitle")}</h2>
          <p>{t("home.testimonialsText")}</p>
        </div>
        <div className="testimonialGrid">
          {testimonials[lang].map((item) => (
            <article className="testimonial" key={item.name}>
              <div className="stars">
                {Array.from({ length: 5 }).map((_, index) => <Star size={16} fill="currentColor" key={index} />)}
              </div>
              <p>"{item.quote}"</p>
              <strong>{item.name}</strong>
              <span>{item.role}</span>
            </article>
          ))}
        </div>
      </section>

      <section className="pricing" id="pricing">
        <div className="sectionHeading">
          <h2>{t("home.pricingTitle")}</h2>
          <p>{t("home.pricingText")}</p>
        </div>
        <div className="pricingGrid">
          {pricing[lang].map(([name, credits, text], index) => (
            <article className={index === 1 ? "priceCard featured" : "priceCard"} key={name}>
              <h3>{name}</h3>
              <strong>{credits}</strong>
              <span>{t("home.monthlyCredits")}</span>
              <p>{text}</p>
              <a href="#api">{t("common.choose")}</a>
            </article>
          ))}
        </div>
      </section>

      <Footer apiUrl={publicApiUrl} />
    </main>
  );
}

function Header({ apiUrl }: { apiUrl: string }) {
  const t = useT();
  return (
    <header className="siteHeader">
      <a className="logo" href="#">
        <span>SC</span>
        Scrapling Cloud
      </a>
      <nav className="navLinks">
        <a href="#features">{t("nav.features")}</a>
        <a href="#api">{t("nav.api")}</a>
        <a href="#pricing">{t("nav.pricing")}</a>
        <a href="/docs">{t("nav.docs")}</a>
      </nav>
      <div className="headerActions">
        <LangSwitch />
        <a className="signIn" href="/login">{t("common.signIn")}</a>
        <a className="headerCta" href="/login">{t("common.apiKey")}</a>
      </div>
    </header>
  );
}

function Step({ number, title, text, icon: Icon }: { number: string; title: string; text: string; icon: typeof Bot }) {
  return (
    <article className="step">
      <span>{number}</span>
      <div className="stepIcon"><Icon size={24} /></div>
      <h3>{title}</h3>
      <p>{text}</p>
    </article>
  );
}

function MiniChart({ large = false }: { large?: boolean }) {
  return (
    <svg className={large ? "miniChart large" : "miniChart"} viewBox="0 0 260 120" role="img" aria-label="Usage line chart">
      <path d="M10 100 C40 76 55 84 82 58 C111 30 137 68 164 48 C194 24 218 44 250 18" />
      <circle cx="82" cy="58" r="5" />
      <circle cx="164" cy="48" r="5" />
      <circle cx="250" cy="18" r="5" />
    </svg>
  );
}

function Footer({ apiUrl }: { apiUrl: string }) {
  const t = useT();
  const [lang] = useState<"tr" | "en">("tr");
  return (
    <footer className="footer">
      <div>
        <a className="logo" href="#"><span>SC</span> Scrapling Cloud</a>
        <p>{t("home.footerText")}</p>
      </div>
      <div>
        <strong>{t("home.footerProduct")}</strong>
        <a href="#features">{t("nav.features")}</a>
        <a href="#pricing">{t("nav.pricing")}</a>
        <a href="#customers">{t("nav.customers")}</a>
      </div>
      <div>
        <strong>{t("home.footerDevelopers")}</strong>
        <a href="#api">{t("nav.apiDocs")}</a>
        <a href={`${apiUrl}/docs`}>OpenAPI</a>
        <a href="#features">SDKs</a>
      </div>
      <div>
        <strong>{t("home.footerCompany")}</strong>
        <a href="#api">{t("nav.contact")}</a>
        <a href="#features">{t("nav.security")}</a>
        <a href="#features">Attribution</a>
      </div>
    </footer>
  );
}
