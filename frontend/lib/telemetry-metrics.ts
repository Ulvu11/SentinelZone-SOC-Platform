type Reading = { value: number | null; status: string; unit?: string };
type Sensor = { device_id: string; type: string; reading: Reading };

export function maximumGpuUtilization(sensors: Sensor[]): number | null {
  const values = sensors.filter(sensor => sensor.reading.unit === "percent" &&
    (sensor.type.toLowerCase() === "utilization" || sensor.device_id.toLowerCase().includes("gpu")))
    .map(sensor => sensor.reading.status === "ok" ? sensor.reading.value : null)
    .filter((value): value is number => typeof value === "number" && Number.isFinite(value));
  return values.length ? Math.round(Math.max(...values) * 10) / 10 : null;
}

export function countAboveThreshold(values: (number | null)[], threshold: number): number | null {
  const observed = values.filter((value): value is number => typeof value === "number" && Number.isFinite(value));
  return observed.length ? observed.filter(value => value > threshold).length : null;
}
