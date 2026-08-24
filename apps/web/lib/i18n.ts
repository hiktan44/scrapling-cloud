"use client";

import { useLang, pickByLang } from "./use-lang";

// Translation dictionary with namespace structure
export const DICT = {
  // Navigation
  nav: {
    features: { tr: "Özellikler", en: "Features" },
    api: { tr: "API", en: "API" },
    pricing: { tr: "Fiyatlandırma", en: "Pricing" },
    docs: { tr: "Dokümanlar", en: "Docs" },
    customers: { tr: "Müşteriler", en: "Customers" },
    contact: { tr: "İletişim", en: "Contact" },
    security: { tr: "Güvenlik", en: "Security" },
    apiDocs: { tr: "API dokümanları", en: "API docs" },
    openapi: { tr: "OpenAPI", en: "OpenAPI" },
    sdks: { tr: "SDKs", en: "SDKs" },
    attribution: { tr: "Attribution", en: "Attribution" }
  },

  // Common actions
  common: {
    signIn: { tr: "Giriş yap", en: "Sign in" },
    signUp: { tr: "Kayıt", en: "Sign up" },
    logout: { tr: "Çıkış", en: "Log out" },
    refresh: { tr: "Yenile", en: "Refresh" },
    choose: { tr: "Seç", en: "Choose" },
    open: { tr: "Aç", en: "Open" },
    create: { tr: "Oluştur", en: "Create" },
    new: { tr: "Yeni", en: "New" },
    copy: { tr: "Kopyala", en: "Copy" },
    cancel: { tr: "İptal", en: "Cancel" },
    revoke: { tr: "İptal", en: "Revoke" },
    load: { tr: "Yükle", en: "Load" },
    save: { tr: "Kaydet", en: "Save" },
    delete: { tr: "Sil", en: "Delete" },
    edit: { tr: "Düzenle", en: "Edit" },
    view: { tr: "Görüntüle", en: "View" },
    start: { tr: "Başlat", en: "Start" },
    submit: { tr: "Gönder", en: "Submit" },
    back: { tr: "Geri", en: "Back" },
    close: { tr: "Kapat", en: "Close" },
    apiKey: { tr: "API key al", en: "Get API key" }
  },

  // Authentication
  auth: {
    loginTitle: { tr: "Panele giriş yap", en: "Sign in to dashboard" },
    signupTitle: { tr: "Yeni workspace oluştur", en: "Create new workspace" },
    loginDesc: { tr: "API key üretmek, kullanımını görmek ve scraping işlerini takip etmek için dashboard'a gir.", en: "Enter dashboard to generate API keys, track usage and monitor scraping jobs." },
    loginTab: { tr: "Giriş", en: "Login" },
    signupTab: { tr: "Kayıt", en: "Sign up" },
    workspaceName: { tr: "Workspace adı", en: "Workspace name" },
    email: { tr: "E-posta", en: "Email" },
    password: { tr: "Şifre", en: "Password" },
    enterDashboard: { tr: "Dashboard'a gir", en: "Enter dashboard" },
    createAccount: { tr: "Hesap oluştur", en: "Create account" },
    loginFailed: { tr: "Giriş yapılamadı", en: "Login failed" },
    unexpectedError: { tr: "Beklenmeyen hata oluştu", en: "Unexpected error occurred" },
    freeCredits: { tr: "Ücretsiz başlangıç kredisi", en: "Free starting credits" },
    endpoint: { tr: "Endpoint", en: "Endpoint" }
  },

  // Admin panel
  admin: {
    admin: { tr: "Admin", en: "Admin" },
    userAndCreditManagement: { tr: "Kullanıcı ve kredi yönetimi", en: "User and credit management" },
    organizations: { tr: "Organizasyonlar", en: "Organizations" },
    creditManagement: { tr: "Kredi yönetimi", en: "Credit management" },
    userKeys: { tr: "Kullanıcı key", en: "User keys" },
    dataExplorer: { tr: "Data Explorer", en: "Data Explorer" },
    docs: { tr: "Docs", en: "Docs" },
    workspace: { tr: "Workspace", en: "Workspace" },
    totalCredits: { tr: "Toplam kredi", en: "Total credits" },
    used: { tr: "Kullanılan", en: "Used" },
    selectedRemaining: { tr: "Seçili kalan", en: "Selected remaining" },
    allUsers: { tr: "Tüm kullanıcılar", en: "All users" },
    allUsersDesc: { tr: "Workspace seç, kredi ve API key işlemlerini o kullanıcı/organizasyon için uygula.", en: "Select a workspace to apply credit and API key operations for that user/organization." },
    noEmail: { tr: "E-posta yok", en: "No email" },
    remainingCredits: { tr: "kalan kredi", en: "remaining credits" },
    addCredits: { tr: "Kredi yükle", en: "Add credits" },
    addCreditsDesc: { tr: "Kredi, plan ve concurrency ayarları.", en: "Credit, plan and concurrency settings." },
    selectWorkspace: { tr: "Önce bir workspace seç.", en: "Select a workspace first." },
    credits: { tr: "Kredi", en: "Credits" },
    plan: { tr: "Plan", en: "Plan" },
    concurrency: { tr: "Concurrency", en: "Concurrency" },
    addCredit: { tr: "Kredi ekle", en: "Add credit" },
    setMonthlyLimit: { tr: "Aylık limiti yap", en: "Set monthly limit" },
    resetUsage: { tr: "Kullanımı sıfırla", en: "Reset usage" },
    generateApiKey: { tr: "Kullanıcı için API key üret", en: "Generate API key for user" },
    generateApiKeyDesc: { tr: "Bu key sadece bir kez gösterilir; müşteriye veya kendi uygulamana Bearer token olarak ver.", en: "This key is shown only once; give it to customer or use as Bearer token in your app." },
    keyName: { tr: "Key adı", en: "Key name" },
    createApiKey: { tr: "API key oluştur", en: "Create API key" },
    newUserApiKey: { tr: "Yeni kullanıcı API key'i", en: "New user API key" },
    customerProductionKey: { tr: "Customer production key", en: "Customer production key" },
    creditsLoaded: { tr: "Kredi yüklendi", en: "Credits loaded" },
    monthlyLimitUpdated: { tr: "Aylık kredi limiti güncellendi", en: "Monthly credit limit updated" },
    usageReset: { tr: "Kullanım sıfırlandı", en: "Usage reset" },
    creditsUpdateError: { tr: "Kredi güncellenemedi", en: "Failed to update credits" },
    apiKeyCreated: { tr: "için API key oluşturuldu", en: "API key created for" },
    apiKeyCreateError: { tr: "API key oluşturulamadı", en: "Failed to create API key" },
    adminRequestFailed: { tr: "Admin isteği başarısız oldu", en: "Admin request failed" },
    adminLoadError: { tr: "Admin panel yüklenemedi", en: "Failed to load admin panel" },
    adminDataLoading: { tr: "Admin verileri yükleniyor", en: "Loading admin data" },
    forWorkspace: { tr: "için", en: "for" }
  },

  // Docs page
  docs: {
    quickStart: { tr: "Hızlı başlangıç", en: "Quick start" },
    apiDocumentation: { tr: "API Dokümantasyonu", en: "API Documentation" },
    sdkMcp: { tr: "SDK & MCP", en: "SDK & MCP" },
    sdkMcpDesc: { tr: "Resmi Python istemcisi ve MCP server ile kod içinden veya AI istemcilerinden erişin.", en: "Access from code or AI clients with official Python client and MCP server." }
  },

  // Homepage
  home: {
    heroTitle: { tr: "Temiz web verisine ihtiyaç duyan ürünler için scraping altyapısı", en: "Scraping infrastructure for products that need clean web data" },
    heroText: { tr: "Scrapling Cloud, Scrapling'i Firecrawl benzeri bir SaaS platformuna dönüştürür: API key, kredi, webhook, doküman ve güvenli domain öğrenmesiyle scrape, crawl, map ve extract.", en: "Scrapling Cloud turns Scrapling into a Firecrawl-style SaaS: scrape, crawl, map and extract with API keys, credits, webhooks, docs and safe domain learning." },
    primaryCta: { tr: "Kullanmaya başla", en: "Start building" },
    docsCta: { tr: "API dokümanları", en: "View API docs" },
    trust: { tr: "Coolify üzerinde self-host", en: "Self-host on Coolify" },
    trust2: { tr: "Stripe kredi sistemi", en: "Stripe credits" },
    trust3: { tr: "Scrapling destekli", en: "Scrapling powered" },
    featureTitle: { tr: "Tüm temel scraping iş akışları kutu kutu hazır", en: "Every core scraping workflow, boxed and ready" },
    featureText: { tr: "Canlı renkli ürün modülleri platformu anlaşılır tutar; API ise geliştirici dostu kalır.", en: "Colorful product modules keep the platform easy to understand while the API stays developer-first." },
    workflowTitle: { tr: "URL'den temiz veriye üç adımda", en: "From URL to clean data in three steps" },
    workflowText: { tr: "İnsanlar için dashboard, uygulamalarınız için REST API.", en: "Use the dashboard for humans and the REST API for your applications." },
    analyticsTitle: { tr: "Kullanım, kredi ve öğrenme sinyalleri tek yerde", en: "Usage, credits and learning signals in one place" },
    analyticsText: { tr: "Worker loglarında kaybolmadan tüketimi, iş durumlarını, concurrency'yi, webhook teslimatını ve önerileri takip edin.", en: "Track consumption, job status, concurrency, webhook delivery and recommendations without digging through worker logs." },
    analyticsBullet1: { tr: "Plan bazlı concurrency ve aylık krediler", en: "Plan-based concurrency and monthly credits" },
    analyticsBullet2: { tr: "Uygulamalarınız için async job callback'leri", en: "Async job callbacks for your apps" },
    analyticsBullet3: { tr: "Domain politikaları ve saygılı hız sınırlama", en: "Domain policies and respectful throttling" },
    docsTitle: { tr: "Ürünün içinde geliştirici dokümanları", en: "Developer docs built into the product" },
    docsText: { tr: "Müşterileriniz hızlı başlasın diye OpenAPI, curl örnekleri ve SDK kullanımlarını dashboard yanında yayınlayın.", en: "Publish OpenAPI, curl snippets and SDK examples next to the dashboard so your customers can start quickly." },
    openDocs: { tr: "FastAPI dokümanını aç", en: "Open FastAPI docs" },
    testimonialsTitle: { tr: "Veri ürünü geliştiren ekipler için tasarlandı", en: "Built for teams shipping data products" },
    testimonialsText: { tr: "Geliştiriciler için net API'ler, operasyon için görünür kullanım, müşteriler için basit kontroller.", en: "Clear APIs for developers, visible usage for operators, simple controls for customers." },
    pricingTitle: { tr: "API kullanımına net oturan paketler", en: "Plans that map cleanly to API usage" },
    pricingText: { tr: "Stripe abonelikleri, aylık krediler ve plan bazlı limitler Coolify dağıtımı için hazır.", en: "Stripe subscriptions, monthly credits and plan-based limits are ready for Coolify deployment." },
    choosePlan: { tr: "Paketi seç", en: "Choose plan" },
    footerText: { tr: "Scrapling destekli self-hosted scraping API altyapısı.", en: "Self-hosted scraping API infrastructure powered by Scrapling." },
    footerProduct: { tr: "Ürün", en: "Product" },
    footerDevelopers: { tr: "Geliştiriciler", en: "Developers" },
    footerCompany: { tr: "Şirket", en: "Company" },
    monthlyCredits: { tr: "aylık kredi", en: "monthly credits" },
    queued: { tr: "kuyruğa alındı", en: "queued" },
    successRateLive: { tr: "Başarı oranı (canlı)", en: "Success rate (live)" },
    step1Title: { tr: "Key oluştur", en: "Create a key" },
    step1Text: { tr: "Production, staging veya müşteriye özel entegrasyonlar için scoped API key üretin.", en: "Generate scoped API keys for production, staging or customer-specific integrations." },
    step2Title: { tr: "Job gönder", en: "Send a job" },
    step2Text: { tr: "Scrape, crawl, map, extract veya batch endpoint'lerini tahmin edilebilir JSON payload'larıyla çağırın.", en: "Call scrape, crawl, map, extract or batch endpoints with predictable JSON payloads." },
    step3Title: { tr: "Güvenle öğren", en: "Learn safely" },
    step3Text: { tr: "Başarılı selector ve render stratejileri domain bazında sonraki çalışmaları iyileştirir.", en: "Successful selectors and render strategies improve future runs by domain." },
    smallApps: { tr: "Küçük uygulamalar ve iç araçlar", en: "Small apps and internal tools" },
    productionApps: { tr: "Production uygulamalar ve ekipler", en: "Production apps and teams" },
    highVolume: { tr: "Yüksek hacimli veri hatları", en: "High-volume pipelines" },
    custom: { tr: "Özel", en: "Custom" },
    feature1Title: { tr: "Scrape", en: "Scrape" },
    feature1Text: { tr: "Her sayfeyi tahmin edilebilir API yanıtlarıyla markdown, html, text, link, metadata ve screenshot formatlarına dönüştürün.", en: "Turn any page into markdown, html, text, links, metadata and screenshots with predictable API responses." },
    feature2Title: { tr: "Crawl", en: "Crawl" },
    feature2Text: { tr: "Depth, limit, include/exclude kuralları, canlı job durumları ve webhook callback'leriyle async site crawl çalıştırın.", en: "Run async site crawls with depth, limits, include/exclude rules, live job states and webhook callbacks." },
    feature3Title: { tr: "Map", en: "Map" },
    feature3Text: { tr: "Tam extraction akışına kredi harcamadan önce URL'leri, sitemap'leri ve link graph'larını keşfedin.", en: "Discover URLs, sitemaps and link graphs before you spend credits on full extraction workflows." },
    feature4Title: { tr: "Extract", en: "Extract" },
    feature4Text: { tr: "Bir schema gönderin; ürün sayfaları, dokümanlar, makaleler ve veri setleri için structured JSON alın.", en: "Send a schema and receive structured JSON for product pages, docs, articles and internal datasets." },
    feature5Title: { tr: "API Keys", en: "API Keys" },
    feature5Text: { tr: "Scoped key oluşturun, secret rotate edin, son kullanım bilgisini görün ve production/development ortamlarını ayırın.", en: "Create scoped keys, rotate secrets, track last-used activity and separate production from development." },
    feature6Title: { tr: "Güvenli Öğrenme", en: "Safe Learning" },
    feature6Text: { tr: "Başarılı job'lardan domain stratejileri öğrenilir; otomasyonun production kodunu yeniden yazmasına izin verilmez.", en: "Learn domain strategies from successful jobs without letting automation rewrite production code." },
    quote1: { tr: "Scraping, crawl job'ları ve structured extraction'ı bir haftada tek API arkasına taşıdık. Domain learning sinyalleri hataları çok daha kolay anlaşılır yaptı.", en: "We moved scraping, crawl jobs and structured extraction behind one API in a week. The domain learning signals made failures much easier to debug." },
    quote2: { tr: "Kredi modeli ürün ekipleri için yeterince net, altyapı için yeterince kontrollü. Gerçek SaaS operasyonu için tasarlanmış gibi.", en: "The credit model is clear enough for product teams and strict enough for infrastructure. It feels built for real SaaS operations." },
    quote3: { tr: "Uygulamalarımız tek endpoint çağırıyor, temiz markdown veya JSON alıyor. Dashboard destek ekibine tam gereken job geçmişini veriyor.", en: "Our apps call one endpoint, then receive clean markdown or JSON. The dashboard gives support exactly the job history they need." }
  },

  // Dashboard
  dashboard: {
    dashboard: { tr: "Dashboard", en: "Dashboard" },
    overview: { tr: "Genel bakış", en: "Overview" },
    apiKeys: { tr: "API key", en: "API keys" },
    admin: { tr: "Admin", en: "Admin" },
    playground: { tr: "Playground", en: "Playground" },
    batchAnalysis: { tr: "Toplu Analiz", en: "Batch Analysis" },
    dataExplorer: { tr: "Data Explorer", en: "Data Explorer" },
    docs: { tr: "Docs", en: "Docs" },
    plan: { tr: "Plan", en: "Plan" },
    remainingCredits: { tr: "Kalan kredi", en: "Credits remaining" },
    usedCredits: { tr: "Kullanılan kredi", en: "Used credits" },
    concurrency: { tr: "Concurrency", en: "Concurrency" },
    apiKeyManagement: { tr: "API key yönetimi", en: "API key management" },
    apiKeyDesc: { tr: "Uygulamalarında Bearer token olarak kullanacağın key'leri buradan oluştur.", en: "Create keys here to use as Bearer tokens in your applications." },
    newKey: { tr: "Yeni key", en: "New key" },
    newKeyWarning: { tr: "Yeni key, sadece şimdi gösterilir", en: "New key shown only once" },
    active: { tr: "aktif", en: "active" },
    revoked: { tr: "iptal edildi", en: "revoked" },
    liveTestArea: { tr: "Canlı test alanı", en: "Live test area" },
    playgroundReady: { tr: "Scrape Playground ayrı sekmede hazır", en: "Scrape Playground ready in separate tab" },
    playgroundDesc: { tr: "URL gönder, formats/mode seç, ilerlemeyi canlı izle ve sonucu geniş ekranda incele.", en: "Send URL, choose formats/mode, watch progress live and review result on large screen." },
    openPlayground: { tr: "Playground'u aç", en: "Open Playground" },
    batchAnalysisTitle: { tr: "Toplu analiz", en: "Batch analysis" },
    batchAnalysisDesc: { tr: "Excel yükle, sosyal medya ve firma analizi al", en: "Upload Excel, get social media and company analysis" },
    batchAnalysisDesc2: { tr: "Site listeni .xlsx, .csv veya .txt olarak yükle; her site için sosyal medya hesapları ve kısa firma analizi içeren Excel raporu indir.", en: "Upload your site list as .xlsx, .csv or .txt; download Excel report containing social media accounts and brief company analysis for each site." },
    openBatchAnalysis: { tr: "Toplu Analizi aç", en: "Open Batch Analysis" },
    dataExtraction: { tr: "Derin veri çıkarımı", en: "Deep data extraction" },
    dataExplorerTitle: { tr: "Data Explorer ile tüm sayfaları tara", en: "Scan all pages with Data Explorer" },
    dataExplorerDesc: { tr: "Başlangıç URL'sinden aynı domain içinde derinlere in, sayfa metinlerini ve linkleri okunabilir kartlarda gör.", en: "Go deep within the same domain from starting URL, view page texts and links in readable cards." },
    openDataExplorer: { tr: "Data Explorer'ı aç", en: "Open Data Explorer" },
    recentJobs: { tr: "Son işler", en: "Recent jobs" },
    recentJobsDesc: { tr: "API üzerinden oluşturulan son scrape, crawl, map ve extract job'ları.", en: "Recent scrape, crawl, map and extract jobs created via API." },
    noJobs: { tr: "Henüz job yok.", en: "No jobs yet." },
    credits: { tr: "kredi", en: "credits" },
    dashboardLoading: { tr: "Dashboard yükleniyor", en: "Loading dashboard" },
    dashboardLoadError: { tr: "Dashboard yüklenemedi", en: "Failed to load dashboard" },
    apiKeyCreateError: { tr: "Key oluşturulamadı", en: "Failed to create key" },
    apiKeyRevokeError: { tr: "Key iptal edilemedi", en: "Failed to revoke key" },
    apiRequestFailed: { tr: "API isteği başarısız oldu", en: "API request failed" },
    productionKey: { tr: "Production key", en: "Production key" },
    activeJobs: { tr: "Aktif işler", en: "Active jobs" },
    weeklyUsage: { tr: "Haftalık kullanım", en: "Weekly usage" }
  }
} as const;

// Translation function with nested key support
export function t(key: string, lang: import("./use-lang").Lang, vars?: Record<string, string | number>): string {
  const keys = key.split(".");
  let value: any = DICT;
  
  for (const k of keys) {
    if (value && typeof value === "object" && k in value) {
      value = value[k];
    } else {
      // Key not found, return the key itself as fallback
      return key;
    }
  }
  
  // If we reached the end and have a translation object, get the language value
  if (value && typeof value === "object" && lang in value) {
    let result = value[lang];
    
    // Replace variables if provided
    if (vars && typeof result === "string") {
      Object.entries(vars).forEach(([varKey, varValue]) => {
        result = result.replace(new RegExp(`{${varKey}}`, "g"), String(varValue));
      });
    }
    
    return result;
  }
  
  // Fallback to Turkish if available
  if (value && typeof value === "object" && "tr" in value) {
    return value.tr;
  }
  
  // Last resort: return the key
  return key;
}

// Hook that combines useLang and t
export function useT(): (key: string, vars?: Record<string, string | number>) => string {
  const [lang] = useLang();
  return (key: string, vars?: Record<string, string | number>) => t(key, lang, vars);
}

// Export helper for use in server components or other contexts
export { pickByLang, useLang };

// Export types
export type { Lang } from "./use-lang";