"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { formatTime } from "@/lib/format";
import type { IncidentDetail, AIAnalysis, Endpoint } from "@/types";
import { PageHeader } from "@/components/page-header";
import { SeverityBadge } from "@/components/severity-badge";
import { IncidentStatusBadge } from "@/components/status-badge";
import { Timeline } from "@/components/timeline";
import { SectionHeader } from "@/components/section-header";
import { LoadingState } from "@/components/loading-state";
import { ErrorState } from "@/components/error-state";
import {
  Bot,
  ArrowLeft,
  Clock,
  User,
  Server,
  Globe,
  Target,
  Shield,
  ChevronRight,
} from "lucide-react";

export default function IncidentDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysis | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const [endpoints, setEndpoints] = useState<Endpoint[]>([]);

  useEffect(() => {
    let active = true;
    Promise.all([api.getIncidentDetail(id), api.getEndpoints()])
      .then(([data, assets]) => {
        if (active) {
          setIncident(data);
          setEndpoints(assets);
          setLoading(false);
        }
      })
      .catch(() => {
        if (active) {
          setError("Unable to load incident data. Please retry.");
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [id]);

  const handleAnalyze = async () => {
    if (!incident) return;
    setAnalyzing(true);
    setError("");
    try {
      const result = await api.analyzeWithAI(
        "Analyze incident " + incident.id + ": " + incident.title,
      );
      setAiAnalysis(result);
    } catch {
      setError("Analysis could not be completed. Please try again.");
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading) return <LoadingState message="Loading incident details..." />;
  if (!incident)
    return (
      <>
        <Link href="/incidents" className="link">
          Back to Incidents
        </Link>
        <ErrorState
          title="Incident unavailable"
          message={error || "No incident matches this ID."}
        />
      </>
    );

  return (
    <div>
      <Link
        href="/incidents"
        className="inline-flex items-center gap-1.5 text-sm text-soc-muted hover:text-soc-accent mb-4 transition-colors"
      >
        <ArrowLeft size={14} />
        Back to Incidents
      </Link>

      <PageHeader
        eyebrow={`Incident ${incident.id}`}
        title={incident.title}
        actions={
          <div className="flex flex-wrap items-center gap-3">
            <SeverityBadge severity={incident.severity} />
            <IncidentStatusBadge status={incident.status} />
            <button
              onClick={handleAnalyze}
              disabled={analyzing}
              className="flex items-center gap-2 px-4 py-2 bg-soc-accent text-white rounded-lg text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              <Bot size={16} />
              {analyzing ? "Analyzing..." : "Analyze with AI"}
            </button>
          </div>
        }
      />

      <section className="mb-5 rounded-lg border border-soc-line bg-soc-panel p-4">
        <SectionHeader title="Overview" />
        <p className="text-sm text-soc-muted">{incident.description}</p>
        <p className="mt-2 text-xs">
          Assigned analyst: {incident.assignedTo ?? "Unassigned"}
        </p>
      </section>
      {error && (
        <p role="alert" className="mb-4 text-sm text-soc-danger">
          {error}
        </p>
      )}
      {/* Incident metadata grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-6">
        <div className="bg-soc-surface border border-soc-line rounded-lg p-3">
          <div className="text-xs text-soc-muted mb-1 flex items-center gap-1">
            <Shield size={12} /> Confidence
          </div>
          <div className="text-sm font-semibold">{incident.confidence}%</div>
        </div>
        <div className="bg-soc-surface border border-soc-line rounded-lg p-3">
          <div className="text-xs text-soc-muted mb-1 flex items-center gap-1">
            <Server size={12} /> Affected Asset
          </div>
          <div className="text-sm font-semibold break-words">
            {endpoints.find((e) => e.hostname === incident.affectedAsset) ? (
              <Link
                className="link"
                href={
                  "/endpoints/" +
                  endpoints.find((e) => e.hostname === incident.affectedAsset)
                    ?.id
                }
              >
                {incident.affectedAsset}
              </Link>
            ) : (
              <Link
                className="link"
                href={
                  incident.affectedAsset === "COWRIE-01"
                    ? "/honeypots"
                    : "/network"
                }
              >
                {incident.affectedAsset}
              </Link>
            )}
          </div>
        </div>
        <div className="bg-soc-surface border border-soc-line rounded-lg p-3">
          <div className="text-xs text-soc-muted mb-1 flex items-center gap-1">
            <User size={12} /> Affected User
          </div>
          <div className="text-sm font-semibold">{incident.affectedUser}</div>
        </div>
        <div className="bg-soc-surface border border-soc-line rounded-lg p-3">
          <div className="text-xs text-soc-muted mb-1 flex items-center gap-1">
            <Globe size={12} /> Source IP
          </div>
          <div className="text-sm font-mono">{incident.sourceIp}</div>
        </div>
        <div className="bg-soc-surface border border-soc-line rounded-lg p-3">
          <div className="text-xs text-soc-muted mb-1 flex items-center gap-1">
            <Clock size={12} /> Created
          </div>
          <div className="text-sm">{formatTime(incident.createdAt)}</div>
        </div>
        <div className="bg-soc-surface border border-soc-line rounded-lg p-3">
          <div className="text-xs text-soc-muted mb-1 flex items-center gap-1">
            <Clock size={12} /> Updated
          </div>
          <div className="text-sm">{formatTime(incident.updatedAt)}</div>
        </div>
      </div>

      {/* Detection sources and MITRE */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
        <div className="bg-soc-surface border border-soc-line rounded-lg p-3">
          <div className="text-xs text-soc-muted mb-2">Detection Sources</div>
          <div className="flex flex-wrap gap-1.5">
            {incident.detectionSources.map((s) => (
              <span
                key={s}
                className="px-2 py-1 text-xs bg-soc-panel border border-soc-line rounded-md"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
        <div className="bg-soc-surface border border-soc-line rounded-lg p-3">
          <div className="text-xs text-soc-muted mb-2 flex items-center gap-1">
            <Target size={12} /> MITRE ATT&CK Techniques
          </div>
          <div className="flex flex-wrap gap-1.5">
            {incident.mitreTechniques.map((t) => (
              <Link
                href={"/mitre#" + t}
                key={t}
                className="px-2 py-1 text-xs font-mono bg-soc-accent-bg text-soc-accent rounded-md"
              >
                {t}
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Timeline and Evidence */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <div className="bg-gradient-to-b from-soc-panel-alt to-soc-panel border border-soc-line rounded-xl p-4">
          <SectionHeader title="Investigation Timeline" />
          <Timeline events={incident.timeline} />
        </div>

        <div className="bg-gradient-to-b from-soc-panel-alt to-soc-panel border border-soc-line rounded-xl p-4">
          <SectionHeader title="Evidence" />
          <div className="space-y-2">
            {incident.evidence.map((ev, i) => (
              <div
                key={i}
                className="flex items-start gap-3 p-3 bg-soc-surface border border-soc-line rounded-lg"
              >
                <SeverityBadge severity={ev.severity} />
                <div className="flex-1">
                  <div className="text-xs text-soc-muted mb-0.5">{ev.type}</div>
                  <div className="text-sm font-mono text-soc-text break-all">
                    {ev.value}
                  </div>
                  <div className="text-xs text-soc-muted mt-1">
                    {ev.description}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Related alerts */}
      <div className="bg-gradient-to-b from-soc-panel-alt to-soc-panel border border-soc-line rounded-xl p-4 mb-6">
        <SectionHeader title="Related Alerts" />
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-soc-line">
                <th className="text-left text-xs font-medium text-soc-muted uppercase tracking-wider px-4 py-2">
                  ID
                </th>
                <th className="text-left text-xs font-medium text-soc-muted uppercase tracking-wider px-4 py-2">
                  Title
                </th>
                <th className="text-left text-xs font-medium text-soc-muted uppercase tracking-wider px-4 py-2">
                  Severity
                </th>
                <th className="text-left text-xs font-medium text-soc-muted uppercase tracking-wider px-4 py-2">
                  Source
                </th>
                <th className="text-left text-xs font-medium text-soc-muted uppercase tracking-wider px-4 py-2">
                  Time
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-soc-line">
              {incident.relatedAlerts.map((alert) => (
                <tr key={alert.id} className="hover:bg-soc-surface">
                  <td className="px-4 py-2 font-mono text-xs text-soc-accent">
                    {alert.id}
                  </td>
                  <td className="px-4 py-2">{alert.title}</td>
                  <td className="px-4 py-2">
                    <SeverityBadge severity={alert.severity} />
                  </td>
                  <td className="px-4 py-2">
                    <span className="px-1.5 py-0.5 text-[10px] bg-soc-surface border border-soc-line rounded">
                      {alert.source}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-xs text-soc-muted">
                    {formatTime(alert.timestamp)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <div className="bg-gradient-to-b from-soc-panel-alt to-soc-panel border border-soc-line rounded-xl p-4">
          <SectionHeader title="Investigation Recommendations" />
          <ul className="space-y-2">
            {incident.recommendations.map((rec, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm text-soc-text"
              >
                <ChevronRight
                  size={14}
                  className="text-soc-accent mt-0.5 flex-shrink-0"
                />
                {rec}
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-gradient-to-b from-soc-panel-alt to-soc-panel border border-soc-line rounded-xl p-4">
          <SectionHeader title="Containment Recommendations" />
          <ul className="space-y-2">
            {incident.containmentSteps.map((step, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm text-soc-text"
              >
                <span className="w-5 h-5 rounded-full bg-soc-accent-bg text-soc-accent text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                  {i + 1}
                </span>
                {step}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mb-4 text-sm">
        <Link className="link" href={"/ai-soc?incident=" + incident.id}>
          Open AI investigation workspace →
        </Link>
      </div>
      {/* AI Analysis */}
      {aiAnalysis && (
        <div className="bg-gradient-to-b from-soc-panel-alt to-soc-panel border border-soc-accent/30 rounded-xl p-4">
          <SectionHeader
            title="AI SOC Analysis"
            subtitle={`Confidence: ${aiAnalysis.confidence}%`}
          />

          <div className="space-y-4">
            <div>
              <h4 className="text-xs font-semibold text-soc-muted uppercase tracking-wider mb-2">
                Summary
              </h4>
              <p className="text-sm text-soc-text leading-relaxed">
                {aiAnalysis.summary}
              </p>
            </div>

            <div>
              <h4 className="text-xs font-semibold text-soc-muted uppercase tracking-wider mb-2">
                Evidence
              </h4>
              <ul className="space-y-1">
                {aiAnalysis.evidence.map((e, i) => (
                  <li
                    key={i}
                    className="text-sm text-soc-text flex items-start gap-2"
                  >
                    <span className="text-soc-danger mt-1">•</span>
                    {e}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h4 className="text-xs font-semibold text-soc-muted uppercase tracking-wider mb-2">
                Risk Factors
              </h4>
              <ul className="space-y-1">
                {aiAnalysis.riskFactors.map((r, i) => (
                  <li
                    key={i}
                    className="text-sm text-soc-text flex items-start gap-2"
                  >
                    <span className="text-soc-warn mt-1">•</span>
                    {r}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h4 className="text-xs font-semibold text-soc-muted uppercase tracking-wider mb-2">
                MITRE Techniques
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {aiAnalysis.mitreTechniques.map((t) => (
                  <span
                    key={t}
                    className="px-2 py-1 text-xs font-mono bg-soc-accent-bg text-soc-accent rounded-md"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="text-xs font-semibold text-soc-muted uppercase tracking-wider mb-2">
                  Recommended Investigation
                </h4>
                <ul className="space-y-1">
                  {aiAnalysis.recommendations.map((r, i) => (
                    <li
                      key={i}
                      className="text-sm text-soc-text flex items-start gap-2"
                    >
                      <ChevronRight
                        size={12}
                        className="text-soc-accent mt-1 flex-shrink-0"
                      />
                      {r}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="text-xs font-semibold text-soc-muted uppercase tracking-wider mb-2">
                  Recommended Containment
                </h4>
                <ul className="space-y-1">
                  {aiAnalysis.containmentSteps.map((s, i) => (
                    <li
                      key={i}
                      className="text-sm text-soc-text flex items-start gap-2"
                    >
                      <span className="w-4 h-4 rounded-full bg-soc-accent-bg text-soc-accent text-[9px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                        {i + 1}
                      </span>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
