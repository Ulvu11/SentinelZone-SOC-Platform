// Unified SOC Platform - shared frontend domain types

export type Severity = "critical" | "high" | "medium" | "low";

export type IncidentStatus =
  "open" | "investigating" | "contained" | "resolved";

export type EndpointStatus = "healthy" | "warning" | "critical" | "offline";

export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface OverviewMetrics {
  securityScore: number | null;

  totalEndpoints: number;
  healthyEndpoints: number;
  warningEndpoints: number;
  criticalEndpoints: number;
  offlineEndpoints: number;

  activeIncidents: number;
  criticalIncidents: number;
  highIncidents: number;

  alertsToday: number;
  networkAlerts: number;
  hardwareWarnings: number;
  honeypotActivity: number;
}

export interface Alert {
  id: string;
  title: string;
  description?: string;
  severity: Severity;
  source: string;
  timestamp: string;

  endpointId?: string;
  sourceIp?: string;
  destinationIp?: string;
}

export interface Incident {
  id: string;
  title: string;
  description: string;

  severity: Severity;
  status: IncidentStatus;
  confidence: number;

  affectedAsset: string;
  affectedUser: string;
  sourceIp: string;

  detectionSources: string[];
  mitreTechniques: string[];

  assignedTo?: string;

  createdAt: string;
  updatedAt: string;
}

export interface TimelineEvent {
  id: string;
  timestamp: string;

  // Kept for compatibility with different timeline renderers
  time?: string;

  title: string;
  description?: string;

  source?: string;
  severity?: Severity;
  category?: string;
}

export interface EvidenceItem {
  type: string;
  value: string;
  description: string;
  severity: Severity;
}

export interface IncidentDetail extends Incident {
  timeline: TimelineEvent[];
  evidence: EvidenceItem[];
  relatedAlerts: Alert[];

  recommendations: string[];
  containmentSteps: string[];
}

export interface Endpoint {
  id: string;
  hostname: string;
  ip: string;
  user: string;
  os: string;

  status: EndpointStatus;

  securityRisk: number | null;
  hardwareRisk: number | null;

  cpu: number | null;
  gpu: number | null;
  ram: number | null;
  agentStatus: "online" | "degraded" | "offline";

  lastSeen: string;
}

export interface ProcessInfo {
  pid: number;
  parentPid?: number;

  name: string;
  parentProcess?: string;

  cpu: number | null;
  gpu: number | null;

  path: string;
  signed: boolean | null;

  networkActivity: string;
  risk: number | null;
}

export interface EndpointDetail extends Endpoint {
  ram: number | null;

  cpuTemperature: number | null;
  gpuTemperature: number | null;
  diskTemperature: number | null;

  fanStatus: string;

  userIdleMinutes: number | null;
  networkActivity: string;

  agentStatus: "online" | "degraded" | "offline";

  processes: ProcessInfo[];

  securityRiskReasons: string[];
  hardwareRiskReasons: string[];
  agentId?: string;
  agentVersion?: string;
  platform?: string;
  sensorAvailability?: {name:string;status:string;detail:string}[];
  networkConnections?: {local_address:string;local_port:number;remote_address:string;remote_port:number;state:string;owner_status:string}[];
  persistenceObservations?: {source:string;location:string;executable:string|null;status:string}[];
  unknownData?: string[];
  rulesetVersions?: string[];
}

export interface RiskScore {
  score: number;
  level: RiskLevel;
  reasons: string[];
}

export interface HardwareRisk extends RiskScore {
  cpuTemperature?: number;
  gpuTemperature?: number;
  diskTemperature?: number;
  fanStatus?: string;
}

export interface NetworkAlert {
  id: string;
  title: string;
  severity: Severity;

  source: string;
  sourceIp: string;
  destinationIp: string;

  protocol: string;
  destinationPort?: number;

  action: string;
  timestamp: string;
}

export interface NetworkTraffic {
  timestamp: string;

  inboundMbps: number;
  outboundMbps: number;

  connections: number;
  blockedConnections: number;
}

export interface HoneypotMetrics {
  attacksToday: number;
  uniqueAttackers: number;

  sshAttempts: number;
  successfulDecoyLogins: number;

  commandsExecuted: number;
  filesDownloaded: number;
}

export interface HoneypotCommand {
  timestamp: string;
  command: string;
}

export interface HoneypotSession {
  id: string;

  sourceIp: string;
  username: string;

  startedAt: string;
  durationSeconds: number;

  commands: HoneypotCommand[];

  downloadedFiles: string[];

  severity: Severity;
}

export interface MITRETechnique {
  id: string;
  name: string;
  tactic: string;

  description: string;

  coverage: number;

  incidentIds: string[];
  detectionSources: string[];
}

export interface AIMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface AIAnalysis {
  id: string;
  query: string;
  timestamp: string;

  confidence: number;

  summary: string;

  evidence: string[];
  riskFactors: string[];

  mitreTechniques: string[];

  recommendations: string[];
  containmentSteps: string[];
}

export interface IdentityEvent {
  id: string;

  eventType: string;
  user: string;
  host: string;

  sourceIp: string;

  severity: Severity;

  description: string;
  timestamp: string;
}

export interface EmulationCampaign {
  id: string;
  name: string;

  status: "planned" | "running" | "completed";

  startedAt: string;

  techniques: string[];

  detectedTechniques: string[];
  missedTechniques: string[];
}

export interface BackupStatus {
  id: string;
  system: string;

  status: "healthy" | "warning" | "failed";

  lastBackup: string;

  restoreReady: boolean;
  immutable: boolean;
  protected: boolean;
}

export interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
}

export interface SearchResult {
  id: string;

  type: "ip" | "endpoint" | "incident" | "user" | "process" | "hash";

  label: string;
  description: string;

  href: string;
}

export interface TimeSeriesPoint {
  time: string;
  value: number;
}

export interface ThreatHuntQuery {
  query: string;

  entityType?: "ip" | "hostname" | "username" | "process" | "hash" | "incident";

  timeRange?: string;
}

export interface ThreatHuntResult {
  href?: string;
  id: string;

  entityType: string;
  value: string;

  source: string;
  severity: Severity;

  timestamp: string;
  summary: string;

  relatedIncidentIds: string[];
}
