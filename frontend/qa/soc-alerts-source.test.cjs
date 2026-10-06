const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const Module = require('node:module');
const { test, after } = require('node:test');
function load(relative, overrides = {}) {
  const file = path.resolve(__dirname, relative);
  const code = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const mod = new Module(file, module); mod.filename = file; mod.paths = module.paths;
  const originalRequire = mod.require.bind(mod);
  mod.require = (id) => Object.hasOwn(overrides, id) ? overrides[id] : originalRequire(id);
  mod._compile(code, file); return mod.exports;
}
const normalizer = load('../lib/soc-alerts.ts');
const { readSocAlerts } = load('../lib/soc-alerts-source.ts', { 'server-only': {}, './soc-alerts': normalizer });
const previousFetch = global.fetch;
const previousUrl = process.env.SOC_ALERTS_URL;
after(() => { global.fetch = previousFetch; if (previousUrl === undefined) delete process.env.SOC_ALERTS_URL; else process.env.SOC_ALERTS_URL = previousUrl; });
test('missing or remote configuration never sends a network request', async () => {
  global.fetch = () => { throw new Error('must not fetch'); };
  delete process.env.SOC_ALERTS_URL;
  await assert.rejects(readSocAlerts(), { code: 'not_configured' });
  process.env.SOC_ALERTS_URL = 'http://10.10.100.20:5000/api/alerts';
  await assert.rejects(readSocAlerts(), { code: 'not_configured' });
});
test('outages fail closed with a generic code, not mock alerts or secret error text', async () => {
  process.env.SOC_ALERTS_URL = 'http://127.0.0.1:15000/api/alerts';
  global.fetch = async () => { throw new Error('private detail'); };
  await assert.rejects(readSocAlerts(), { code: 'unavailable', message: 'unavailable' });
  global.fetch = async () => new Response('private detail', { status: 500 });
  await assert.rejects(readSocAlerts(), { code: 'unavailable' });
});
test('invalid JSON and unexpectedly large responses are rejected', async () => {
  global.fetch = async () => new Response('{broken', { headers: { 'content-type': 'application/json' } });
  await assert.rejects(readSocAlerts(), { code: 'invalid_response' });
  global.fetch = async () => new Response('{}', { headers: { 'content-type': 'application/json', 'content-length': '1048577' } });
  await assert.rejects(readSocAlerts(), { code: 'invalid_response' });
});
test('a valid empty response differs from an unavailable source and disables caching/redirects', async () => {
  global.fetch = async (_url, options) => {
    assert.equal(options.cache, 'no-store'); assert.equal(options.redirect, 'error'); assert.ok(options.signal);
    return Response.json({ status: 'ok', alerts: [] });
  };
  const result = await readSocAlerts();
  assert.equal(result.status, 'ok'); assert.equal(result.alerts.length, 0);
});
