export const formatTime = (value: string) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : `${date.toISOString().slice(0, 16).replace("T", " ")} UTC`;
};

export const displayMetric = (value: number | null | undefined, unit = "") => value == null ? "Unavailable" : `${value}${unit}`;

export const riskLevel = (score: number | null) =>
  score === null ? "unknown" : score >= 80
    ? "critical"
    : score >= 50
      ? "high"
      : score >= 20
        ? "medium"
        : "low";

export const isActiveIncident = (status: string) =>
  status === "open" || status === "investigating";
