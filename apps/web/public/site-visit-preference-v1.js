// The choice and daily browser identifier are scoped to this website.
(() => {
  'use strict';
  const config = document.currentScript?.dataset;
  if (!config || location.origin !== config.siteOrigin || document.getElementById('site-visit-preference')) return;
  const choiceKey = 'site-visits:analytics-choice:v1';
  const visitKey = 'site-sayaci:istanbul-day:v1';
  const privacySignal = () => navigator.globalPrivacyControl === true || navigator.doNotTrack === '1';
  function allowed() {
    try { return localStorage.getItem(choiceKey) === 'yes' && !privacySignal(); }
    catch { return false; }
  }
  const language = document.documentElement.lang?.split('-')[0];
  const text = ({
    en: ['Visit measurement', 'Allow this site to count my browser once per day', 'The daily identifier stays on this site. Only totals reach the reporting panel. You can withdraw here at any time.', 'Your browser privacy setting disables measurement.'],
    ar: ['قياس الزيارات', 'أسمح لهذا الموقع بإحصاء متصفحي مرة واحدة في اليوم', 'يبقى المعرّف اليومي في هذا الموقع. تصل الأعداد الإجمالية فقط إلى لوحة التقارير. يمكنك سحب الموافقة هنا في أي وقت.', 'يوقف إعداد الخصوصية في متصفحك القياس.'],
    tr: ['Ziyaret ölçümü', 'Bu sitede tarayıcımın günde bir kez sayılmasına izin veriyorum', 'Günlük kimlik bu sitede kalır. Rapor paneline yalnızca toplamlar gider. Tercihinizi burada değiştirebilirsiniz.', 'Tarayıcınızın gizlilik tercihi ölçümü kapatıyor.']
  })[language] || ['Ziyaret ölçümü', 'Bu sitede tarayıcımın günde bir kez sayılmasına izin veriyorum', 'Günlük kimlik bu sitede kalır. Rapor paneline yalnızca toplamlar gider. Tercihinizi burada değiştirebilirsiniz.', 'Tarayıcınızın gizlilik tercihi ölçümü kapatıyor.'];
  const control = document.createElement('details');
  control.id = 'site-visit-preference';
  const summary = document.createElement('summary');
  summary.textContent = text[0];
  const label = document.createElement('label');
  const toggle = document.createElement('input');
  toggle.type = 'checkbox';
  label.append(toggle, document.createTextNode(' ' + text[1]));
  const detail = document.createElement('p');
  control.append(summary, label, detail);
  document.body.append(control);
  let revision = 0;
  function clearLocalId() {
    try { localStorage.removeItem(visitKey); } catch { /* Storage may be blocked. */ }
  }
  function guestStorage() {
    // Presence is sufficient; never read token values.
    const keys = (config.localSessionKeys || '').split(',').filter(Boolean);
    for (let i = 0; i < localStorage.length; i++) if (keys.includes(localStorage.key(i))) return false;
    return !config.tabSessionKey || !Object.hasOwn(sessionStorage, config.tabSessionKey);
  }
  async function guestSession() {
    if (!guestStorage()) return false;
    if (!config.authProbe) return true;
    const betterAuth = config.authProbe === 'better-auth';
    const response = await fetch(betterAuth ? '/api/auth/get-session' : '/api/auth/me', {
      credentials: 'same-origin', cache: 'no-store', redirect: 'error', referrerPolicy: 'no-referrer'
    });
    if (betterAuth && response.ok) return (await response.json()) === null;
    await response.body?.cancel();
    return !betterAuth && response.status === 401;
  }
  async function sync() {
    const version = ++revision;
    toggle.checked = allowed();
    toggle.disabled = privacySignal();
    detail.textContent = toggle.disabled ? text[3] : text[2];
    if (!toggle.checked) { clearLocalId(); return; }
    if (navigator.webdriver || document.visibilityState !== 'visible') return;
    try {
      if (!await guestSession() || revision !== version || !allowed()) return;
      const { recordPageVisit } = await import('/.well-known/site-visits/client.mjs');
      await recordPageVisit({
        hasAnalyticsConsent: () => revision === version && allowed() && guestStorage(),
        // An unsigned browser cannot establish whether it belongs to the site owner.
        isOwner: () => guestStorage() ? null : true
      });
    } catch { /* Private mode, a blocked request or unavailable identity leaves the app usable. */ }
  }
  toggle.addEventListener('change', () => {
    try { localStorage.setItem(choiceKey, toggle.checked && !privacySignal() ? 'yes' : 'no'); }
    catch { toggle.checked = false; }
    void sync();
  });
  window.addEventListener('site-visits-preference', sync);
  window.addEventListener('storage', event => {
    if (event.key === choiceKey || event.key === null || (config.localSessionKeys || '').split(',').includes(event.key)) void sync();
  });
  window.addEventListener('pageshow', sync);
  window.addEventListener('pagehide', () => { ++revision; });
  document.addEventListener('visibilitychange', sync);
  void sync();
})();
