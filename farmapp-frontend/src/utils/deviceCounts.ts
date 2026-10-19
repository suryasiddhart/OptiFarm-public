import type { Device } from "../types";

/** Number of active devices per field id. */
export function countDevicesByField(devices: Device[]): Record<number, number> {
  const counts: Record<number, number> = {};
  for (const device of devices) {
    if (device.fieldid === null || device.status !== "active") continue;
    counts[device.fieldid] = (counts[device.fieldid] ?? 0) + 1;
  }
  return counts;
}
