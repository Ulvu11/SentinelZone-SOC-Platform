"use client";
import { useState } from "react";
import { Panel } from "@/components/panel";
import { usePreferences } from "@/lib/preferences";
export function SettingsWorkspace({ health }: { health: { connectors: Record<string, {status:string}> } }) {
  const { preferences, save } = usePreferences();
  const [message, setMessage] = useState("");
  const update = (value: Parameters<typeof save>[0]) => {
    try {
      save(value);
      setMessage("Preferences saved in this browser.");
    } catch {
      setMessage(
        "Browser storage is unavailable. Preferences could not be saved.",
      );
    }
  };
  return (
    <div className="space-y-4">
      <nav aria-label="Settings sections" className="flex flex-wrap gap-2">
        {[
          "General",
          "Appearance",
          "Notifications",
          "Integrations",
          "Users & Roles",
          "API",
        ].map((label) => (
          <a
            className="button"
            key={label}
            href={
              "#" + (label === "Users & Roles" ? "users" : label.toLowerCase())
            }
          >
            {label}
          </a>
        ))}
      </nav>
      <p role="status" className="text-xs text-soc-muted">
        {message ||
          "Personal preferences are stored locally. Integration and access settings are read-only."}
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel id="general" title="General">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const data = new FormData(e.currentTarget);
              update({
                workspace: String(data.get("workspace") ?? "Unified SOC"),
              });
            }}
            className="space-y-3"
          >
            <label className="block text-sm">
              Workspace name
              <input
                key={preferences.workspace}
                name="workspace"
                defaultValue={preferences.workspace}
                required
                maxLength={48}
                className="control mt-2 block w-full"
              />
            </label>
            <p className="text-xs text-soc-muted">
              Observation timestamps use UTC across the workspace.
            </p>
            <button className="button">Save workspace name</button>
          </form>
        </Panel>
        <Panel id="appearance" title="Appearance">
          <p className="mb-4 text-sm text-soc-muted">
            Enterprise dark theme · deep blue surfaces
          </p>
          <label className="text-sm">
            Table density
            <select
              aria-label="Table density"
              className="control ml-3"
              value={preferences.density}
              onChange={(e) =>
                update({ density: e.target.value as "compact" | "comfortable" })
              }
            >
              <option value="comfortable">Comfortable</option>
              <option value="compact">Compact</option>
            </select>
          </label>
        </Panel>
        <Panel id="notifications" title="Notifications">
          <label className="flex items-center gap-3 text-sm">
            <input
              type="checkbox"
              checked={preferences.highlightAlerts}
              onChange={(e) => update({ highlightAlerts: e.target.checked })}
            />
            Highlight the alerts shortcut
          </label>
          <p className="mt-3 text-xs text-soc-muted">
            Controls the visual alert indicator in this browser. Email and push
            delivery are not configured.
          </p>
        </Panel>
        <Panel
          id="integrations"
          title="Integrations"
          subtitle="Live connector state from SentinelZone"
        >
          <div className="grid grid-cols-2 gap-2">
            {Object.keys(health.connectors).map((source) => (
              <div
                key={source}
                className="rounded-md border border-soc-line p-2 text-xs"
              >
                {source}
                <span className="ml-2 text-soc-muted">
                  {health.connectors[source].status}
                </span>
              </div>
            ))}
          </div>
        </Panel>
      </div>
      <Panel
        id="users"
        title="Users & Roles"
        subtitle="Workspace access reference · changes require identity service integration"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-soc-muted">
                <th scope="col" className="py-2">
                  User
                </th>
                <th scope="col">Role</th>
                <th scope="col">Access</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-soc-line">
                <td className="py-3">Dashboard service</td>
                <td>Viewer</td>
                <td>Read persisted evidence; user administration is unavailable here</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Panel>
      <Panel
        id="api"
        title="API"
        subtitle="Connection settings are managed through the frontend environment"
      >
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs text-soc-muted">Data mode</dt>
            <dd>
              SentinelZone backend
            </dd>
          </div>
          <div>
            <dt className="text-xs text-soc-muted">Connection</dt>
            <dd className="font-mono text-xs">Server-side authenticated proxy</dd>
          </div>
        </dl>
        <p className="mt-4 text-xs text-soc-muted">
          All data requests use the shared API abstraction. API keys and server
          credentials are never stored in these preferences.
        </p>
      </Panel>
    </div>
  );
}
