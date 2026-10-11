const assert = require('node:assert/strict');
const { test } = require('node:test');
const { readFileSync, existsSync } = require('node:fs');
const { resolve, dirname } = require('node:path');
const { createRequire } = require('node:module');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

const root = resolve(__dirname, '..');
const modules = new Map();

// Projenin gerçek TS/TSX dosyaları ve gerçek React/Next bağımlılıkları kullanılır.
function loadSource(filename) {
  if (modules.has(filename)) return modules.get(filename).exports;
  const mod = { exports: {} };
  modules.set(filename, mod);
  const requirePackage = createRequire(filename);
  function requireSource(specifier) {
    if (!specifier.startsWith('.')) return requirePackage(specifier);
    const base = resolve(dirname(filename), specifier);
    const target = [base, base + '.ts', base + '.tsx'].find(existsSync);
    if (!target) throw new Error('Kaynak bağımlılığı bulunamadı: ' + specifier);
    return loadSource(target);
  }
  const compiled = ts.transpileModule(readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
    fileName: filename,
  }).outputText;
  const evaluate = vm.runInThisContext('(function(require,module,exports){' + compiled + '\n})', { filename });
  evaluate(requireSource, mod, mod.exports);
  return mod.exports;
}

globalThis.fetch = async () => { throw new Error('Web regresyon testi dış ağa erişemez.'); };

test('API anahtarı sunucu renderinde depolamadan okunmaz ve çıktıya taşınmaz', () => {
  let reads = 0;
  globalThis.window = { localStorage: { getItem() { reads++; return 'codex-fictional-private-key'; } } };
  try {
    const { useStoredApiKey, useStoredValue } = loadSource(resolve(root, 'lib/use-stored-value.ts'));
    function Probe() {
      const key = useStoredApiKey();
      const workspace = useStoredValue('scrapling_cloud_workspace');
      return React.createElement('p', null, key + (workspace ?? 'Çalışma alanı'));
    }
    assert.equal(renderToStaticMarkup(React.createElement(Probe)), '<p>Çalışma alanı</p>');
    assert.equal(reads, 0);
  } finally {
    delete globalThis.window;
  }
});

test('Dil menüsünün sunucu çıktısı Türkçe, tutarlı ve erişilebilir olur', () => {
  globalThis.window = { localStorage: { getItem() { throw new Error('Sunucuda depolama okunamaz'); } } };
  try {
    const LangSwitch = loadSource(resolve(root, 'components/LangSwitch.tsx')).default;
    const html = renderToStaticMarkup(React.createElement(LangSwitch));
    assert.match(html, /aria-label="Dil seçimi"/);
    assert.match(html, /aria-label="Türkçeye geç" aria-pressed="true"/);
    assert.match(html, /aria-label="İngilizceye geç" aria-pressed="false"/);
  } finally {
    delete globalThis.window;
  }
});

for (const [page, expected] of [
  ['admin', 'Müşteri üretim anahtarı'],
  ['dashboard', 'Çalışma alanı'],
  ['data', 'Analiz talimatı'],
  ['batch', 'Scrapling Cloud'],
  ['playground', 'Scrapling Cloud'],
  ['docs', 'veri toplama, site tarama'],
]) {
  test(page + ' ekranı gerçek React renderinde depolama ve dış ağ olmadan açılır', () => {
    const Page = loadSource(resolve(root, 'app', page, 'page.tsx')).default;
    const html = renderToStaticMarkup(React.createElement(Page));
    assert.ok(html.includes(expected));
    assert.ok(!html.includes('codex-fictional-private-key'));
  });
}

// Dil saklama ve bildirim sözleşmesi, gerçek tarayıcı yerine izole fikstürlerle sınanır.
function clientLanguageFixture({ stored = null, cookie = '', blocked = false } = {}) {
  const target = new EventTarget();
  const values = new Map(stored === null ? [] : [['ui_lang', stored]]);
  target.localStorage = {
    getItem(key) { if (blocked) throw new Error('Depolama kapalı'); return values.get(key) ?? null; },
    setItem(key, value) { if (blocked) throw new Error('Depolama kapalı'); values.set(key, value); },
  };
  globalThis.window = target;
  globalThis.document = blocked ? { get cookie() { throw new Error('Çerez kapalı'); }, set cookie(_value) { throw new Error('Çerez kapalı'); } } : { cookie };
  let subscribe;
  const hooks = {
    useCallback: callback => callback,
    useSyncExternalStore: (listener, read) => { subscribe = listener; return read(); },
  };
  const filename = resolve(root, 'lib/use-lang.ts');
  const code = ts.transpileModule(readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 }, fileName: filename,
  }).outputText;
  const mod = { exports: {} };
  vm.runInThisContext('(function(require,module,exports){' + code + '\n})', { filename })(
    name => { assert.equal(name, 'react'); return hooks; }, mod, mod.exports,
  );
  const result = {
    language: mod.exports.useLang,
    subscribe: callback => subscribe(callback),
    values,
    event(key) { const event = new Event('storage'); Object.defineProperty(event, 'key', { value: key }); target.dispatchEvent(event); },
    cleanup() { delete globalThis.window; delete globalThis.document; },
  };
  result.language();
  return result;
}

test('Kaydedilmiş dil, çerez tercihinden önce kullanılır', () => {
  const fixture = clientLanguageFixture({ stored: 'en', cookie: 'ui_lang=tr' });
  try { assert.equal(fixture.language()[0], 'en'); } finally { fixture.cleanup(); }
});

test('Depolama tercihi yoksa geçerli dil çerezi kullanılır', () => {
  const fixture = clientLanguageFixture({ cookie: 'another=value; ui_lang=en' });
  try { assert.equal(fixture.language()[0], 'en'); } finally { fixture.cleanup(); }
});

test('Geçersiz tercihlerde varsayılan dil Türkçe kalır', () => {
  const fixture = clientLanguageFixture({ stored: 'de', cookie: 'ui_lang=fr' });
  try { assert.equal(fixture.language()[0], 'tr'); } finally { fixture.cleanup(); }
});

test('Dil değişimi kaydedilir, diğer abonelere bildirilir ve abonelik kapatılabilir', () => {
  const fixture = clientLanguageFixture();
  try {
    let notices = 0;
    const close = fixture.subscribe(() => notices++);
    fixture.language()[1]('en');
    assert.equal(fixture.language()[0], 'en');
    assert.equal(fixture.values.get('ui_lang'), 'en');
    assert.match(document.cookie, /^ui_lang=en;/);
    assert.equal(notices, 1);
    close();
    fixture.language()[1]('tr');
    assert.equal(notices, 1);
  } finally { fixture.cleanup(); }
});

test('Depolama ve çerez kapalıyken dil değişimi oturum içinde çalışır', () => {
  const fixture = clientLanguageFixture({ blocked: true });
  try {
    assert.equal(fixture.language()[0], 'tr');
    fixture.language()[1]('en');
    assert.equal(fixture.language()[0], 'en');
  } finally { fixture.cleanup(); }
});

test('Başka sekmedeki dil tercihi güncellenir; ilgisiz depolama olayları dili değiştirmez', () => {
  const fixture = clientLanguageFixture();
  try {
    let notices = 0;
    const close = fixture.subscribe(() => notices++);
    fixture.language()[1]('en');
    fixture.values.set('ui_lang', 'tr');
    fixture.event('other_key');
    assert.equal(fixture.language()[0], 'en');
    fixture.event('ui_lang');
    assert.equal(fixture.language()[0], 'tr');
    assert.equal(notices, 2);
    close();
  } finally { fixture.cleanup(); }
});
