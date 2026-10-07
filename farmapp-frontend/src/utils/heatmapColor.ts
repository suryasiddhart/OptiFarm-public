/**
 * Maps a moisture percentage value to a hex color.
 * @param moisture - Moisture value (0-100). null means no data.
 * @returns Hex color string.
 */
export function moistureToColor(moisture: number | null): string {
  if (moisture === null) return "#e0e0e0"; // grey = no data

  if (moisture >= 80) return "#1b5e20"; // dark green — very wet
  if (moisture >= 60) return "#4caf50"; // green — moist
  if (moisture >= 40) return "#ffeb3b"; // yellow — moderate
  if (moisture >= 20) return "#ff9800"; // orange — low
  return "#f44336"; // red — dry
}

/**
 * Returns a human-readable label for a moisture level.
 */
export function moistureLabel(moisture: number | null): string {
  if (moisture === null) return "No data";
  if (moisture >= 80) return "Very wet";
  if (moisture >= 60) return "Moist";
  if (moisture >= 40) return "Moderate";
  if (moisture >= 20) return "Low";
  return "Dry";
}
