/** A short "x minutes/hours/days ago" string for activity feeds. */
export function timeAgo(isoString: string, now: number = Date.now()): string {
  const diffSeconds = Math.max(0, Math.floor((now - new Date(isoString).getTime()) / 1000));
  const units: [number, string][] = [
    [31536000, "y"],
    [2592000, "mo"],
    [86400, "d"],
    [3600, "h"],
    [60, "m"],
  ];
  for (const [secondsPerUnit, label] of units) {
    const value = Math.floor(diffSeconds / secondsPerUnit);
    if (value >= 1) return `${value}${label} ago`;
  }
  return "just now";
}
