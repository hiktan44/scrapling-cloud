"use client";

import {
  ArrowRight,
  BookOpenText,
  Bot,
  Braces,
  Check,
  Code2,
  DatabaseZap,
  FileJson2,
  Gauge,
  Globe2,
  KeyRound,
  LineChart,
  LockKeyhole,
  Map,
  Play,
  Radar,
  ShieldCheck,
  Sparkles,
  Star,
  Webhook,
  Zap
} from "lucide-react";
import { useState } from "react";

type Locale = "en" | "tr";

const copy = {
  en: {
    nav: ["Features", "API", "Pricing", "Docs"],
    signIn: "Sign in",
    getKey: "Get API key",
    heroTitle: "Scraping infrastructure for products that need clean web data",
    heroText:
      "Scrapling Cloud turns Scrapling into a Firecrawl-style SaaS: scrape, crawl, map and extract with API keys, credits, webhooks, docs and safe domain learning.",
    primaryCta: "Start building",
    docsCta: "View API docs",
    trust: ["Self-host on Coolify", "Stripe credits", "Scrapling powered"],
    featureTitle: "Every core scraping workflow, boxed and ready",
    featureText: "Colorful product modules keep the platform easy to understand while the API stays developer-first.",
    workflowTitle: "From URL to clean data in three steps",
    workflowText: "Use the dashboard for humans and the REST API for your applications.",
    analyticsTitle: "Usage, credits and learning signals in one place",
    analyticsText:
      "Track consumption, job status, concurrency, webhook delivery and recommendations without digging through worker logs.",
    analyticsBullets: [
      "Plan-based concurrency and monthly credits",
      "Async job callbacks for your apps",
      "Domain policies and respectful throttling"
    ],
    docsTitle: "Developer docs built into the product",
    docsText: "Publish OpenAPI, curl snippets and SDK examples next to the dashboard so your customers can start quickly.",
    openDocs: "Open FastAPI docs",
    testimonialsTitle: "Built for teams shipping data products",
    testimonialsText: "Clear APIs for developers, visible usage for operators, simple controls for customers.",
    pricingTitle: "Plans that map cleanly to API usage",
    pricingText: "Stripe subscriptions, monthly credits and plan-based limits are ready for Coolify deployment.",
    choosePlan: "Choose plan",
    footerText: "Self-hosted scraping API infrastructure powered by Scrapling.",
    footerProduct: "Product",
    footerDevelopers: "Developers",
    footerCompany: "Company",
    metrics: ["Credits remaining", "Active jobs", "Weekly usage", "8 concurrent workers", "monthly credits"],
    codeStatus: "→ 200 queued"
  },
  tr: {
    nav: ["Özellikler", "API", "Fiyatlandırma", "Dokümanlar"],
    signIn: "Giriş yap",
    getKey: "API key al",
    heroTitle: "Temiz web verisine ihtiyaç duyan ürünler için scraping altyapısı",
    heroText:
      "Scrapling Cloud, Scrapling’i Firecrawl benzeri bir SaaS platformuna dönüştürür: API key, kredi, webhook, doküman ve güvenli domain öğrenmesiyle scrape, crawl, map ve extract.",
    primaryCta: "Kullanmaya başla",
    docsCta: "API dokümanları",
    trust: ["Coolify üzerinde self-host", "Stripe kredi sistemi", "Scrapling destekli"],
    featureTitle: "Tüm temel scraping iş akışları kutu kutu hazır",
    featureText: "Canlı renkli ürün modülleri platformu anlaşılır tutar; API ise geliştirici dostu kalır.",
    workflowTitle: "URL’den temiz veriye üç adımda",
    workflowText: "İnsanlar için dashboard, uygulamalarınız için REST API.",
    analyticsTitle: "Kullanım, kredi ve öğrenme sinyalleri tek yerde",
    analyticsText:
      "Worker loglarında kaybolmadan tüketimi, iş durumlarını, concurrency’yi, webhook teslimatını ve önerileri takip edin.",
    analyticsBullets: [
      "Plan bazlı concurrency ve aylık krediler",
      "Uygulamalarınız için async job callback’leri",
      "Domain politikaları ve saygılı hız sınırlama"
    ],
    docsTitle: "Ürünün içinde geliştirici dokümanları",
    docsText: "Müşterileriniz hızlı başlasın diye OpenAPI, curl örnekleri ve SDK kullanımlarını dashboard yanında yayınlayın.",
    openDocs: "FastAPI dokümanını aç",
    testimonialsTitle: "Veri ürünü geliştiren ekipler için tasarlandı",
    testimonialsText: "Geliştiriciler için net API’ler, operasyon için görünür kullanım, müşteriler için basit kontroller.",
    pricingTitle: "API kullanımına net oturan paketler",
    pricingText: "Stripe abonelikleri, aylık krediler ve plan bazlı limitler Coolify dağıtımı için hazır.",
    choosePlan: "Paketi seç",
    footerText: "Scrapling destekli self-hosted scraping API altyapısı.",
    footerProduct: "Ürün",
    footerDevelopers: "Geliştiriciler",
    footerCompany: "Şirket",
    metrics: ["Kalan kredi", "Aktif işler", "Haftalık kullanım", "8 eşzamanlı worker", "aylık kredi"],
    codeStatus: "→ 200 kuyruğa alındı"
  }
} as const;

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
  const [locale, setLocale] = useState<Locale>("tr");
  const t = copy[locale];

  return (
    <main>
      <Header locale={locale} setLocale={setLocale} />
      <section className="hero">
        <div className="heroCopy">
          <h1>{t.heroTitle}</h1>
          <p>
            {t.heroText}
          </p>
          <div className="heroActions">
            <a className="primary" href="#pricing">
              {t.primaryCta}
              <ArrowRight size={18} />
            </a>
            <a className="secondary" href="#api">
              {t.docsCta}
              <BookOpenText size={18} />
            </a>
          </div>
          <div className="trustRow">
            {t.trust.map((item) => <span key={item}><Check size={16} /> {item}</span>)}
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

${t.codeStatus}
{
  "id": "job_7H9K",
  "status": "running",
  "credits": 1
}`}</pre>
          </div>
          <div className="chartCard floating">
            <div>
              <span>{locale === "tr" ? "Başarı oranı" : "Success rate"}</span>
              <strong>97.4%</strong>
            </div>
            <MiniChart />
          </div>
        </div>
      </section>

      <section className="featureBand" id="features">
        <div className="sectionHeading">
          <h2>{t.featureTitle}</h2>
          <p>{t.featureText}</p>
        </div>
        <div className="featureGrid">
          {features[locale].map((feature) => (
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
          <h2>{t.workflowTitle}</h2>
          <p>{t.workflowText}</p>
        </div>
        <div className="steps">
          <Step number="01" title={locale === "tr" ? "Key oluştur" : "Create a key"} text={locale === "tr" ? "Production, staging veya müşteriye özel entegrasyonlar için scoped API key üretin." : "Generate scoped API keys for production, staging or customer-specific integrations."} icon={LockKeyhole} />
          <Step number="02" title={locale === "tr" ? "Job gönder" : "Send a job"} text={locale === "tr" ? "Scrape, crawl, map, extract veya batch endpoint’lerini tahmin edilebilir JSON payload’larıyla çağırın." : "Call scrape, crawl, map, extract or batch endpoints with predictable JSON payloads."} icon={Code2} />
          <Step number="03" title={locale === "tr" ? "Güvenle öğren" : "Learn safely"} text={locale === "tr" ? "Başarılı selector ve render stratejileri domain bazında sonraki çalışmaları iyileştirir." : "Successful selectors and render strategies improve future runs by domain."} icon={Bot} />
        </div>
      </section>

      <section className="analytics">
        <div className="analyticsCopy">
          <h2>{t.analyticsTitle}</h2>
          <p>{t.analyticsText}</p>
          <ul>
            {t.analyticsBullets.map((item, index) => {
              const icons = [Gauge, Webhook, ShieldCheck];
              const Icon = icons[index];
              return <li key={item}><Icon size={18} /> {item}</li>;
            })}
          </ul>
        </div>
        <div className="analyticsBoard">
          <div className="metricCard tealMetric">
            <span>{t.metrics[0]}</span>
            <strong>49,982</strong>
            <div className="meter"><i /></div>
          </div>
          <div className="metricCard">
            <span>{t.metrics[1]}</span>
            <strong>12</strong>
            <p>{t.metrics[3]}</p>
          </div>
          <div className="graphPanel">
            <div className="graphHeader">
              <span>{t.metrics[2]}</span>
              <LineChart size={18} />
            </div>
            <MiniChart large />
          </div>
        </div>
      </section>

      <section className="apiSection" id="api">
        <div className="apiCopy">
          <h2>{t.docsTitle}</h2>
          <p>{t.docsText}</p>
          <a className="secondary" href="http://localhost:8000/docs">
            {t.openDocs}
            <ArrowRight size={18} />
          </a>
        </div>
        <div className="docsCard">
          <div className="docTabs">
            <span className="selected">curl</span>
            <span>TypeScript</span>
            <span>Python</span>
          </div>
          <pre>{`curl -X POST http://localhost:8000/v1/scrape \\
  -H "Authorization: Bearer sk_demo_local_development_key" \\
  -H "Content-Type: application/json" \\
  -d '{"url":"https://example.com","formats":["markdown","links"]}'`}</pre>
        </div>
      </section>

      <section className="testimonials" id="customers">
        <div className="sectionHeading">
          <h2>{t.testimonialsTitle}</h2>
          <p>{t.testimonialsText}</p>
        </div>
        <div className="testimonialGrid">
          {testimonials[locale].map((item) => (
            <article className="testimonial" key={item.name}>
              <div className="stars">
                {Array.from({ length: 5 }).map((_, index) => <Star size={16} fill="currentColor" key={index} />)}
              </div>
              <p>“{item.quote}”</p>
              <strong>{item.name}</strong>
              <span>{item.role}</span>
            </article>
          ))}
        </div>
      </section>

      <section className="pricing" id="pricing">
        <div className="sectionHeading">
          <h2>{t.pricingTitle}</h2>
          <p>{t.pricingText}</p>
        </div>
        <div className="pricingGrid">
          {pricing[locale].map(([name, credits, text], index) => (
            <article className={index === 1 ? "priceCard featured" : "priceCard"} key={name}>
              <h3>{name}</h3>
              <strong>{credits}</strong>
              <span>{t.metrics[4]}</span>
              <p>{text}</p>
              <a href="#api">{t.choosePlan}</a>
            </article>
          ))}
        </div>
      </section>

      <Footer locale={locale} />
    </main>
  );
}

function Header({ locale, setLocale }: { locale: Locale; setLocale: (locale: Locale) => void }) {
  const t = copy[locale];
  return (
    <header className="siteHeader">
      <a className="logo" href="#">
        <span>SC</span>
        Scrapling Cloud
      </a>
      <nav className="navLinks">
        <a href="#features">{t.nav[0]}</a>
        <a href="#api">{t.nav[1]}</a>
        <a href="#pricing">{t.nav[2]}</a>
        <a href="http://localhost:8000/docs">{t.nav[3]}</a>
      </nav>
      <div className="headerActions">
        <div className="languageSwitch" aria-label="Language selector">
          <button className={locale === "tr" ? "selected" : ""} onClick={() => setLocale("tr")}>TR</button>
          <button className={locale === "en" ? "selected" : ""} onClick={() => setLocale("en")}>EN</button>
        </div>
        <a className="signIn" href="#api">{t.signIn}</a>
        <a className="headerCta" href="#pricing">{t.getKey}</a>
      </div>
    </header>
  );
}

function Step({ number, title, text, icon: Icon }: { number: string; title: string; text: string; icon: typeof Zap }) {
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

function Footer({ locale }: { locale: Locale }) {
  const t = copy[locale];
  return (
    <footer className="footer">
      <div>
        <a className="logo" href="#"><span>SC</span> Scrapling Cloud</a>
        <p>{t.footerText}</p>
      </div>
      <div>
        <strong>{t.footerProduct}</strong>
        <a href="#features">{t.nav[0]}</a>
        <a href="#pricing">{t.nav[2]}</a>
        <a href="#customers">{locale === "tr" ? "Müşteriler" : "Customers"}</a>
      </div>
      <div>
        <strong>{t.footerDevelopers}</strong>
        <a href="#api">{locale === "tr" ? "API dokümanları" : "API docs"}</a>
        <a href="http://localhost:8000/docs">OpenAPI</a>
        <a href="#features">SDKs</a>
      </div>
      <div>
        <strong>{t.footerCompany}</strong>
        <a href="#api">{locale === "tr" ? "İletişim" : "Contact"}</a>
        <a href="#features">{locale === "tr" ? "Güvenlik" : "Security"}</a>
        <a href="#features">Attribution</a>
      </div>
    </footer>
  );
}
