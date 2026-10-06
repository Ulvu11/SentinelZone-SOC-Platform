import fs from "node:fs";
import vm from "node:vm";
import assert from "node:assert/strict";
import ts from "typescript";
const compile = (
  file,
  require = () => {
    throw new Error("Unexpected dependency");
  },
) => {
  const exports = {};
  vm.runInNewContext(
    ts.transpileModule(fs.readFileSync(file, "utf8"), {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2022,
      },
    }).outputText,
    { exports, require, process: { env: {} }, setTimeout },
  );
  return exports;
};
const data = compile("lib/mock-data.ts");
const { api } = compile("lib/api.ts", (id) => {
  assert.equal(id, "@/lib/mock-data");
  return data;
});
for (const endpoint of data.mockEndpoints) {
  const detail = await api.getEndpointDetail(endpoint.id);
  for (const key of Object.keys(endpoint))
    assert.equal(detail[key], endpoint[key], endpoint.id + " " + key);
  assert.ok(detail.processes.length);
}
for (const incident of data.mockIncidents) {
  const detail = await api.getIncidentDetail(incident.id);
  assert.ok(
    detail.evidence.length &&
      detail.timeline.length &&
      detail.relatedAlerts.length,
    incident.id,
  );
  for (const technique of incident.mitreTechniques)
    assert.ok(
      data.mockMitreTechniques.some(
        (t) => t.id === technique && t.incidentIds.includes(incident.id),
      ),
    );
}
for (const result of data.mockSearchResults) {
  const path = result.href.split("#")[0];
  if (path.startsWith("/endpoints/"))
    assert.ok(await api.getEndpointDetail(path.split("/")[2]));
  else if (path.startsWith("/incidents/"))
    assert.ok(await api.getIncidentDetail(path.split("/")[2]));
  else assert.fail("Unverified search route " + path);
}
assert.equal(data.mockOverview.totalEndpoints, data.mockEndpoints.length);
assert.equal(
  data.mockOverview.activeIncidents,
  data.mockIncidents.filter((i) => ["open", "investigating"].includes(i.status))
    .length,
);
assert.equal(data.mockEndpointDetail["EP-001"].securityRisk, 94);
assert.equal(data.mockEndpointDetail["EP-001"].hardwareRisk, 68);
assert.equal(
  data.mockIncidentDetail["INC-0042"].affectedAsset,
  "FINANCE-PC-021",
);
for (const [entityType, query] of [
  ["ip", "185.220.101.42"],
  ["hostname", "FINANCE-PC-021"],
  ["username", "a.mammadov"],
  ["process", "svhost64.exe"],
  ["hash", data.suspiciousHash],
  ["incident", "INC-0042"],
]) {
  const hits = await api.threatHunt({ query, entityType, timeRange: "24h" });
  assert.ok(hits.length, entityType);
  assert.ok(hits.every((r) => r.entityType === entityType));
}
assert.equal(
  (await api.threatHunt({ query: "does-not-exist", timeRange: "24h" })).length,
  0,
);
assert.notEqual(
  (await api.analyzeWithAI("INC-0041")).summary,
  (await api.analyzeWithAI("INC-0042")).summary,
);
assert.equal(await api.getEndpointDetail("missing"), null);
assert.equal(await api.getIncidentDetail("missing"), null);
console.log(
  "PASS: canonical inventory, incident evidence, MITRE mappings, search destinations, six hunt types, missing records and incident-specific analysis.",
);
