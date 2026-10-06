import "server-only";
import { eventPage } from "./sentinelzone-data";
import { backend } from "./sentinelzone-backend";
import type { SocAlertSnapshot } from "./soc-alerts";
export { BackendError as AlertSourceError } from "./sentinelzone-backend";
export async function readSocAlerts(range = "24h"):Promise<SocAlertSnapshot> {
  const hours=range==="1h"?1:range==="7d"?168:24;
  const from=new Date(Date.now()-hours*3600000).toISOString();
  const query="&from="+encodeURIComponent(from);
  const [page,overview,health]=await Promise.all([eventPage(query),backend<{events_total:number;open_incidents_total:number}>("/v1/overview?from="+encodeURIComponent(from)),backend<{connectors:Record<string,{status:string;last_event_at:string|null}>;sensors:Record<string,{status:string;last_seen?:string|null}>}>("/v1/telemetry-health")]);
  const alerts=page.items.filter(e=>e.event_type!=="telemetry").map(e=>({id:e.event_uid,source:e.original_sensor,title:e.summary??e.event_type,severity:e.original_severity,eventTime:e.event_time,receivedAt:e.received_at,agentName:e.host_id,agentIp:e.agent_ip,sourceIp:e.src_ip,destinationIp:e.dst_ip,ruleId:null}));
  return {status:"ok",fetchedAt:new Date().toISOString(),limit:500,returnedRecords:alerts.length,rejectedRecords:0,duplicateRecords:0,newestEventAt:alerts[0]?.eventTime??null,alerts,overview,health,hasMore:!!page.next_cursor};
}
