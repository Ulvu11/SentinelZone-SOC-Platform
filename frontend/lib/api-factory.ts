import type { OverviewMetrics, Incident, IncidentDetail, Endpoint, EndpointDetail, NetworkAlert, NetworkTraffic, HoneypotMetrics, HoneypotSession, MITRETechnique, AIAnalysis, Alert, EmulationCampaign, BackupStatus, ReportTemplate, SearchResult, IdentityEvent, ThreatHuntResult, ThreatHuntQuery } from "@/types";
export type DataRequest = <T>(path: string, body?: unknown) => Promise<T>;
export function createApi(request: DataRequest) {
  return {
    getAlerts: () => request<Alert[]>("alerts"),
    getOverview: () => request<OverviewMetrics>("overview"),
    getIncidents: () => request<Incident[]>("incidents"),
    getIncidentDetail: (id: string) => request<IncidentDetail | null>(`incidents/${encodeURIComponent(id)}`),
    getEndpoints: () => request<Endpoint[]>("endpoints"),
    getEndpointDetail: (id: string) => request<EndpointDetail | null>(`endpoints/${encodeURIComponent(id)}`),
    getNetworkAlerts: () => request<NetworkAlert[]>("network/alerts"),
    getNetworkTraffic: () => request<NetworkTraffic[]>("network/traffic"),
    getHoneypotMetrics: () => request<HoneypotMetrics>("honeypots/metrics"),
    getHoneypotSessions: () => request<HoneypotSession[]>("honeypots/sessions"),
    getMitreTechniques: () => request<MITRETechnique[]>("mitre/techniques"),
    analyzeWithAI: (query: string) => request<AIAnalysis>("ai/analyze",{query}),
    getIdentityEvents: () => request<IdentityEvent[]>("identity/events"),
    getEmulationCampaigns: () => request<EmulationCampaign[]>("purple-team/campaigns"),
    getBackupStatus: () => request<BackupStatus[]>("backup/status"),
    getReportTemplates: () => request<ReportTemplate[]>("reports/templates"),
    search: (query: string) => request<SearchResult[]>(`search?q=${encodeURIComponent(query)}`),
    threatHunt: (query: ThreatHuntQuery) => request<ThreatHuntResult[]>("threat-hunting/search",query),
  };
}
