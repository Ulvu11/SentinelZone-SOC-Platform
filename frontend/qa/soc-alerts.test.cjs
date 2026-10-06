const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const Module = require('node:module');
const { test } = require('node:test');
const file = path.resolve(__dirname, '../lib/soc-alerts.ts');
const compiled = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
const adapter = new Module(file, module);
adapter.filename = file; adapter.paths = module.paths; adapter._compile(compiled, file);
const { parseEventTime, sourceSeverity, normalizeAlertFeed, filterAlerts } = adapter.exports;
const row = (extra = {}) => ({ id: 2004, source: 'Wazuh', severity: '10', event_time: '1790759731.850', received_at: '2026-09-30 13:20:54', agent_ip: '10.10.100.10', src_ip: '10.10.30.10', ...extra });
test('epoch seconds retain milliseconds; timezone-free dates stay unknown', () => {
  assert.equal(parseEventTime('1790759731.850'), '2026-09-30T09:15:31.850Z');
  assert.equal(parseEventTime('2026-09-30 13:20:54'), null);
  const record = normalizeAlertFeed({ alerts: [row({ event_time: '' })] }).alerts[0];
  assert.equal(record.eventTime, null); assert.equal(record.receivedAt, '2026-09-30 13:20:54');
});
test('source severity and host/source identity are preserved', () => {
  const record = normalizeAlertFeed({ alerts: [row()] }).alerts[0];
  assert.equal(sourceSeverity(record), 'Wazuh level 10');
  assert.equal(record.agentIp, '10.10.100.10'); assert.equal(record.sourceIp, '10.10.30.10');
  assert.equal(sourceSeverity({ source: 'Suricata', severity: '2' }), '2');
  assert.equal(normalizeAlertFeed({ alerts: [row({ source: 'SOC' })] }).alerts[0].source, 'SOC');
});
test('invalid responses never become empty healthy results', () => {
  for (const payload of [{}, { status: 'error', alerts: [] }, { alerts: [null, {}] }, { alerts: Array(51).fill(row()) }]) assert.throws(() => normalizeAlertFeed(payload));
  assert.equal(normalizeAlertFeed({ status: 'ok', alerts: [] }).returnedRecords, 0);
});
test('feed counts are bounded and duplicates or rejected rows remain visible', () => {
  const result = normalizeAlertFeed({ count: 9999, alerts: [row(), row(), {}, row({ id: 2005 })] });
  assert.equal(result.returnedRecords, 4); assert.equal(result.alerts.length, 2);
  assert.equal(result.rejectedRecords, 1); assert.equal(result.duplicateRecords, 1);
  assert.equal('activeIncidents' in result, false);
});
test('filters use current time and exclude future/unknown event times', () => {
  const now = Date.parse('2026-09-30T10:00:00Z');
  const alerts = normalizeAlertFeed({ alerts: [row(), row({ id: 2, event_time: '2026-09-29T01:00:00Z' }), row({ id: 3, event_time: '2026-10-01T00:00:00Z' }), row({ id: 4, event_time: null })] }).alerts;
  assert.deepEqual(filterAlerts(alerts, '1h', now).map((a) => a.id), ['2004']);
  assert.equal(filterAlerts(alerts, '24h', now, 'Cowrie').length, 0);
  assert.equal(filterAlerts(alerts, '24h', now, 'Wazuh', '10.10.30.10').length, 1);
});
test('unneeded fields and credentials do not leave the adapter', () => {
  const record = normalizeAlertFeed({ alerts: [row({ command: 'secret', password: 'secret', token: 'secret', url: 'https://example.test/?token=secret' })] }).alerts[0];
  assert.equal(JSON.stringify(record).includes('secret'), false);
});
