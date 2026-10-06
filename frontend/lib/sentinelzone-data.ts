import "server-only";
import { backend, BackendError } from "./sentinelzone-backend";
import { maximumGpuUtilization } from "./telemetry-metrics";
import type { Alert, EndpointDetail, Incident, IncidentDetail, NetworkAlert, OverviewMetrics } from "@/types";
type Page<T> = { items: T[]; next_cursor?: string | number | null };
type Event = { event_uid: string; event_time: string; received_at: string; source: string; original_sensor: string; summary: string | null; host_id: string | null; agent_id: string | null; agent_ip: string | null; src_ip: string | null; dst_ip: string | null; dst_port: number | null; normalized_priority: Alert["severity"]; original_severity: string | null; event_type: string; session_id: string | null };
type BackendIncident = { id: string; title: string; summary: string; priority: Incident["severity"]; status: string; confidence: number; host_id: string | null; original_sensors: string[]; reason_codes: string[]; owner: string | null; opened_at: string; updated_at: string; last_seen: string };
type Metric = { value: number | null; status: string; source?: string; unit?: string };
type Risk = { process_instance_id: string; security_risk: number; resource_impact: number | null; reasons: string[]; unknown_data: string[]; lifecycle: string; model_version: string | null; ruleset_version: string };
type Process = { pid: number; ppid: number | null; process_instance_id: string; exe_path: string | null; cpu_percent_host_capacity: Metric; gpu_percent: Metric; file_trust: { status: string; trust_type: string } };
type Connection = { process_instance_id: string | null; local_address: string; local_port: number; remote_address: string; remote_port: number; state: string; owner_status: string };
type Snapshot = { host: { hostname: string; platform: string; os_version: string; architecture: string; cpu_percent: Metric; memory_used_percent: Metric; idle_seconds: Metric }; processes: Process[]; connections: Connection[]; persistence: { source: string; location: string; executable: string | null; status: string }[]; sensors: { name: string; type: string; device_id: string; reading: Metric }[]; coverage: { name: string; status: string; detail: string }[] };
type Agent = { agent_id: string; host_id: string; platform: string; agent_version: string | null; status: string; last_observed_at: string | null; last_received_at: string | null; security_risk: number | null; resource_impact: number | null; snapshot: Snapshot | null; risks: Risk[] };
type Asset = { host_id: string; agent_id: string | null; agent_ip: string | null; last_seen: string; sources: string[] };
type Overview = { events_total: number; open_incidents_total: number; open_incidents_by_priority: Record<string, number>; data_complete: boolean; connectors: Record<string, {status:string;last_event_at:string|null}> };
export async function eventPage(query = "") { return backend<Page<Event>>(`/v1/alerts?limit=500&include_test=false&exclude_telemetry=true${query}`); }
async function pages<T>(path: string, maxPages = 20): Promise<T[]> {
  const out: T[] = []; let cursor: string | number | null | undefined;
  for (let i=0;i<maxPages;i++) { const p=await backend<Page<T>>(`${path}${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`); out.push(...p.items); cursor=p.next_cursor; if(!cursor)return out; }
  throw new BackendError("inventory_limit_exceeded");
}
const metric = (m?: Metric) => m?.status === "ok" && typeof m.value === "number" ? Math.round(m.value*10)/10 : null;
const alert = (e: Event): Alert => ({ id:e.event_uid,title:e.summary??e.event_type,severity:e.normalized_priority,source:e.original_sensor,timestamp:e.event_time,endpointId:e.host_id??undefined,sourceIp:e.src_ip??undefined,destinationIp:e.dst_ip??undefined });
const incident = (i: BackendIncident): Incident => ({ id:i.id,title:i.title,description:i.summary,severity:i.priority,status:({NEW:"open",INVESTIGATING:"investigating",CONTAINED:"contained",RESOLVED:"resolved",CLOSED:"resolved"} as Record<string,Incident["status"]>)[i.status]??"open",confidence:i.confidence,affectedAsset:i.host_id??"Not attributed",affectedUser:"Not provided",sourceIp:"Not provided",detectionSources:i.original_sensors,mitreTechniques:[],assignedTo:i.owner??undefined,createdAt:i.opened_at,updatedAt:i.updated_at });
async function incidents() { return (await pages<BackendIncident>("/v1/incidents?limit=200&execution_mode=REAL")).map(incident); }
function endpoint(a: Agent, assets: Asset[]): EndpointDetail {
  const s=a.snapshot,h=s?.host;
  const resource=a.resource_impact;
  const asset=assets.find(x=>x.host_id===h?.hostname);
  const sensor=(kind:string,type:string)=> { const found=s?.sensors.filter(x=>`${x.name} ${x.device_id}`.toLowerCase().includes(kind)&&x.type.toLowerCase()===type).map(x=>metric(x.reading)).filter((v):v is number=>v!==null)??[]; return found.length?Math.max(...found):null; };
  const cpu=metric(h?.cpu_percent),ram=metric(h?.memory_used_percent),gpu=maximumGpuUtilization(s?.sensors??[]);
  const idle=metric(h?.idle_seconds);
  return { id:a.host_id,hostname:h?.hostname && h.hostname!=="redacted"?h.hostname:a.agent_id,ip:asset?.agent_ip??"Not reported",user:"Not reported",os:h?`${h.platform} · ${h.os_version} · ${h.architecture}`:a.platform,
    status:a.status!=="online"?"offline":(a.security_risk??0)>=80?"critical":(a.security_risk??0)>=50?"warning":"healthy",securityRisk:a.security_risk,hardwareRisk:resource,cpu,gpu,ram,
    agentStatus:a.status==="online"?"online":"offline",lastSeen:a.last_observed_at??"Not observed",cpuTemperature:sensor("cpu","temperature"),gpuTemperature:sensor("gpu","temperature"),diskTemperature:sensor("disk","temperature"),fanStatus:"Not available",userIdleMinutes:idle===null?null:Math.round(idle/60),
    networkActivity:s?`${s.connections.length} observed connections; ownership coverage is reported per connection`:"Not available",
    processes:(s?.processes??[]).map(p=>({pid:p.pid,parentPid:p.ppid??undefined,name:p.exe_path?.split(/[\\/]/).at(-1)??`PID ${p.pid}`,cpu:metric(p.cpu_percent_host_capacity),gpu:metric(p.gpu_percent),path:p.exe_path??"Not available",signed:p.file_trust.trust_type==="authenticode"?(p.file_trust.status==="valid"||p.file_trust.status==="trusted"?true:p.file_trust.status==="unsigned"?false:null):null,networkActivity:(s?.connections??[]).filter(c=>c.process_instance_id===p.process_instance_id).map(c=>`${c.remote_address}:${c.remote_port} (${c.state})`).join(", ")||"No observed owned connection",risk:a.risks.find(r=>r.process_instance_id===p.process_instance_id)?.security_risk??null})),
    securityRiskReasons:[...new Set(a.risks.flatMap(r=>r.reasons))],hardwareRiskReasons:resource===null?["Resource impact unavailable"]:["Measured process resource impact; high usage alone does not indicate malware."],
    agentId:a.agent_id,agentVersion:a.agent_version??"Unknown",platform:a.platform,sensorAvailability:s?.coverage??[],networkConnections:s?.connections??[],persistenceObservations:s?.persistence??[],unknownData:[...new Set(a.risks.flatMap(r=>r.unknown_data))],rulesetVersions:[...new Set(a.risks.map(r=>r.ruleset_version))],
  };
}
async function endpoints(): Promise<EndpointDetail[]> {
  const [agents,assets]=await Promise.all([pages<Agent>("/v1/cryptoguard/agents?limit=100"),pages<Asset>("/v1/assets?limit=500")]);
  return agents.map(a=>endpoint(a,assets));
}
async function detail(id:string):Promise<IncidentDetail|null> {
  try {
    const i=await backend<BackendIncident>(`/v1/incidents/${encodeURIComponent(id)}`);
    const [t,events]=await Promise.all([backend<{items:{id?:string;timestamp?:string;ts?:string;event_time?:string;title?:string;action?:string;summary?:string;detail?:{summary?:string;body?:string;action?:string}}[]}>(`/v1/incidents/${encodeURIComponent(id)}/timeline`),backend<{evidence_ids:string[]}>(`/v1/incidents/${encodeURIComponent(id)}/case-pack`)]);
    const evidenceEvents:Event[]=[];
    for(let offset=0;offset<Math.min(events.evidence_ids.length,200);offset+=10) evidenceEvents.push(...await Promise.all(events.evidence_ids.slice(offset,Math.min(offset+10,200)).map(uid=>backend<Event>(`/v1/alerts/${encodeURIComponent(uid)}`))));
    return {...incident(i),timeline:t.items.map((x,index)=>({id:String(x.id??index),timestamp:x.timestamp??x.ts??x.event_time??i.last_seen,title:x.detail?.summary??x.detail?.body??x.detail?.action??x.title??x.action??x.summary??"Recorded activity"})),evidence:evidenceEvents.map(e=>({type:e.original_sensor,value:e.event_uid,description:e.summary??e.event_type,severity:e.normalized_priority})),relatedAlerts:evidenceEvents.map(alert),recommendations:[],containmentSteps:[]};
  } catch(e){if(e instanceof BackendError&&e.status===404)return null;throw e;}
}
async function overview():Promise<OverviewMetrics> {
  const [o,eps,m]=await Promise.all([backend<Overview>("/v1/overview"),endpoints(),backend<{events_by_source:Record<string,number>}>("/v1/metrics?exclude_telemetry=true&from="+encodeURIComponent(new Date(Date.now()-86400000).toISOString()))]);
  return {securityScore:null,totalEndpoints:eps.length,healthyEndpoints:eps.filter(e=>e.status==="healthy").length,warningEndpoints:eps.filter(e=>e.status==="warning").length,criticalEndpoints:eps.filter(e=>e.status==="critical").length,offlineEndpoints:eps.filter(e=>e.status==="offline").length,activeIncidents:o.open_incidents_total,criticalIncidents:o.open_incidents_by_priority.critical??0,highIncidents:o.open_incidents_by_priority.high??0,alertsToday:Object.values(m.events_by_source).reduce((a,b)=>a+b,0),networkAlerts:m.events_by_source.suricata??0,hardwareWarnings:eps.filter(e=>(e.hardwareRisk??0)>=50).length,honeypotActivity:m.events_by_source.cowrie??0};
}
const network=(e:Event):NetworkAlert=>({id:e.event_uid,title:e.summary??e.event_type,severity:e.normalized_priority,source:e.original_sensor,sourceIp:e.src_ip??"Not provided",destinationIp:e.dst_ip??"Not provided",protocol:"Not retained",destinationPort:e.dst_port??undefined,action:"Observed",timestamp:e.event_time});
export async function readData<T>(path:string,body?:unknown):Promise<T> {
  const [route,query]=path.split("?");const id=decodeURIComponent(route.split("/")[1]??"");let result:unknown;
  if(route==="alerts")result=(await eventPage()).items.filter(e=>e.event_type!=="telemetry").map(alert);
  else if(route==="overview")result=await overview();
  else if(route==="incidents")result=await incidents();
  else if(route.startsWith("incidents/"))result=await detail(id);
  else if(route==="endpoints")result=await endpoints();
  else if(route.startsWith("endpoints/"))result=(await endpoints()).find(e=>e.id===id)??null;
  else if(route==="health")result=await backend("/v1/telemetry-health");
  else if(route==="network/alerts")result=(await eventPage("&source=suricata")).items.filter(e=>e.event_type!=="telemetry").map(network);
  else if(route==="network/traffic"||route==="mitre/techniques"||route==="purple-team/campaigns"||route==="backup/status"||route==="reports/templates")result=[];
  else if(route==="identity/events")result=(await eventPage("&source=wazuh")).items.filter(e=>/auth|login|logon/i.test(e.event_type+" "+e.summary)).map(e=>({id:e.event_uid,eventType:e.event_type,user:"Not retained",host:e.host_id??"Unknown",sourceIp:e.src_ip??"Not provided",severity:e.normalized_priority,description:e.summary??"Wazuh observation",timestamp:e.event_time}));
  else if(route==="honeypots/metrics"||route==="honeypots/sessions") {
    const events=(await pages<Event>("/v1/alerts?limit=500&source=cowrie&from="+encodeURIComponent(new Date(Date.now()-86400000).toISOString())));
    if(route.endsWith("metrics"))result={attacksToday:events.length,uniqueAttackers:new Set(events.map(e=>e.src_ip).filter(Boolean)).size,sshAttempts:events.filter(e=>e.original_severity?.startsWith("cowrie.login.")).length,successfulDecoyLogins:events.filter(e=>e.original_severity==="cowrie.login.success").length,commandsExecuted:events.filter(e=>e.original_severity==="cowrie.command.input").length,filesDownloaded:events.filter(e=>e.original_severity==="cowrie.session.file_download").length};
    else result=[...new Set(events.map(e=>e.session_id).filter(Boolean))].map(id=>{const group=events.filter(e=>e.session_id===id).sort((a,b)=>a.event_time.localeCompare(b.event_time));return {id,sourceIp:group[0].src_ip??"Unknown",username:"Not retained",startedAt:group[0].event_time,durationSeconds:Math.round((Date.parse(group.at(-1)!.event_time)-Date.parse(group[0].event_time))/1000),commands:[],downloadedFiles:[],severity:group.some(e=>e.normalized_priority==="high")?"high":"low"};});
  }
  else if(route==="search") {const q=new URLSearchParams(query).get("q")?.toLowerCase()??"";const [eps,incs]=await Promise.all([endpoints(),incidents()]);result=[...eps.map(e=>({id:e.id,type:"endpoint",label:e.hostname,description:e.ip,href:"/endpoints/"+e.id})),...incs.map(i=>({id:i.id,type:"incident",label:i.title,description:i.description,href:"/incidents/"+i.id}))].filter(r=>`${r.label} ${r.description}`.toLowerCase().includes(q)).slice(0,50);}
  else if(route==="ai/analyze") { const q=(body as {query?:string})?.query??"";const id=q.match(/SZ-\d+/)?.[0];const d=id?await detail(id):null;if(!d)throw new BackendError("incident_not_found",404);result={id:"evidence-"+id,query:q,timestamp:new Date().toISOString(),confidence:d.confidence,summary:d.description,evidence:d.evidence.map(e=>e.description),riskFactors:d.detectionSources.map(s=>"Observed source: "+s),mitreTechniques:[],recommendations:[],containmentSteps:[],assessmentSource:"persisted_evidence"}; }
  else if(route==="threat-hunting/search") {const q=(body as {query?:string})?.query?.toLowerCase()??"";result=(await eventPage()).items.filter(e=>`${e.summary} ${e.host_id} ${e.src_ip}`.toLowerCase().includes(q)).map(e=>({id:e.event_uid,entityType:"event",value:e.host_id??e.src_ip??e.event_uid,source:e.original_sensor,severity:e.normalized_priority,timestamp:e.event_time,summary:e.summary??e.event_type,relatedIncidentIds:[],href:"/alerts"}));}
  else throw new BackendError("not_found",404);
  return result as T;
}
