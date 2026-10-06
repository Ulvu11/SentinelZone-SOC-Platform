"use client";
import { useState } from "react";
import { Download, FileText } from "lucide-react";
import { Panel } from "@/components/panel";
import { reportMarkdown, type ReportDocument } from "@/lib/reports";
export function ReportsWorkspace({ reports }: { reports: ReportDocument[] }) {
  const [selected, setSelected] = useState(reports[0]?.id ?? "");
  const [status, setStatus] = useState("");
  const report = reports.find((r) => r.id === selected);
  const download = () => {
    if (!report) return;
    const url = URL.createObjectURL(
      new Blob([reportMarkdown(report)], {
        type: "text/markdown;charset=utf-8",
      }),
    );
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download =
      report.id + "-" + report.title.toLowerCase().replaceAll(" ", "-") + ".md";
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    setStatus(report.title + " exported as Markdown.");
  };
  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {reports.map((r) => (
          <button
            key={r.id}
            aria-pressed={selected === r.id}
            onClick={() => {
              setSelected(r.id);
              setStatus("");
            }}
            className={
              "rounded-lg border bg-soc-panel p-4 text-left hover:border-soc-accent " +
              (selected === r.id ? "border-soc-accent" : "border-soc-line")
            }
          >
            <FileText size={18} className="mb-3 text-soc-accent" />
            <h2 className="text-sm font-semibold">{r.title}</h2>
            <p className="mt-1 text-xs text-soc-muted">{r.description}</p>
          </button>
        ))}
      </div>
      {report && (
        <Panel
          title={report.title}
          subtitle="Preview · current observation snapshot"
          action={
            <button className="button" onClick={download}>
              <Download size={14} />
              Export report
            </button>
          }
        >
          <div className="space-y-5">
            {report.sections.map((s) => (
              <section key={s.title}>
                <h3 className="mb-2 text-sm font-medium">{s.title}</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr>
                        {s.headers.map((h) => (
                          <th
                            scope="col"
                            key={h}
                            className="border-b border-soc-line px-3 py-2 text-left text-soc-muted"
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {s.rows.map((row, index) => (
                        <tr
                          key={index}
                          className="border-b border-soc-line hover:bg-soc-surface"
                        >
                          {row.map((cell, i) => (
                            <td key={i} className="px-3 py-3">
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            ))}
          </div>
        </Panel>
      )}
      <p role="status" className="text-xs text-soc-good">
        {status}
      </p>
    </div>
  );
}
