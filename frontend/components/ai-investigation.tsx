"use client";
import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { AIAnalysis, Incident } from "@/types";
import { Panel, DetailList } from "@/components/panel";
import { ErrorState } from "@/components/error-state";
export function AIInvestigation({
  incidents,
  initialId,
  initialAnalysis,
}: {
  incidents: Incident[];
  initialId: string;
  initialAnalysis: AIAnalysis;
}) {
  const [id, setId] = useState(initialId);
  const [analysis, setAnalysis] = useState(initialAnalysis);
  const [analyzedId, setAnalyzedId] = useState(initialId);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const analyze = async () => {
    setLoading(true);
    setError("");
    try {
      setAnalysis(await api.analyzeWithAI("Analyze incident " + id));
      setAnalyzedId(id);
    } catch {
      setError("Analysis is unavailable. Retry the selected investigation.");
    } finally {
      setLoading(false);
    }
  };
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm">
          Investigation{" "}
          <select
            className="control ml-2 max-w-full"
            aria-label="Investigation"
            value={id}
            onChange={(e) => setId(e.target.value)}
          >
            {incidents.map((i) => (
              <option key={i.id} value={i.id}>
                {i.id} · {i.title}
              </option>
            ))}
          </select>
        </label>
        <button
          className="button"
          onClick={() => void analyze()}
          disabled={loading}
        >
          {loading ? "Analyzing…" : "Analyze evidence"}
        </button>
        <Link className="link text-xs" href={"/incidents/" + id}>
          Open incident →
        </Link>
      </div>
      {error && <ErrorState message={error} />}
      <Panel
        title="Summary"
        subtitle={
          analyzedId +
          " · " +
          analysis.confidence +
          "% confidence · " +
          "Persisted evidence · AI engine unavailable"
        }
      >
        <p className="text-sm leading-relaxed">{analysis.summary}</p>
        {id !== analyzedId && (
          <p role="status" className="mt-3 text-xs text-soc-warn">
            Showing {analyzedId}. Analyze evidence to update the selected
            investigation.
          </p>
        )}
      </Panel>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Evidence">
          <DetailList items={analysis.evidence} />
        </Panel>
        <Panel title="Risk Factors">
          <DetailList items={analysis.riskFactors} />
        </Panel>
      </div>
      <Panel title="MITRE Mapping">
        <div className="flex flex-wrap gap-2">
          {analysis.mitreTechniques.map((t) => (
            <Link key={t} className="badge link" href={"/mitre#" + t}>
              {t}
            </Link>
          ))}
        </div>
      </Panel>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Recommended Investigation">
          <DetailList items={analysis.recommendations} />
        </Panel>
        <Panel title="Recommended Containment">
          <DetailList items={analysis.containmentSteps} />
        </Panel>
      </div>
      <p className="text-xs text-soc-muted">
        Decision support for the analyst. Recommendations do not execute
        containment actions.
      </p>
    </div>
  );
}
