export interface ActivityDay {
  date: string; // YYYY-MM-DD (UTC)
  count: number;
  level: 0 | 1 | 2 | 3 | 4;
  /** False for cells after "today" that only exist to keep the grid rectangular. */
  inRange: boolean;
}

const DAY_MS = 24 * 60 * 60 * 1000;

function isoDateUtc(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10);
}

function levelFor(count: number): 0 | 1 | 2 | 3 | 4 {
  if (count <= 0) return 0;
  if (count <= 2) return 1;
  if (count <= 5) return 2;
  if (count <= 10) return 3;
  return 4;
}

/**
 * Turns a UTC-date -> count map into a GitHub-style contribution grid: an
 * array of `weeks` columns, each a Sunday-to-Saturday array of 7 days,
 * ending on the week containing `todayMs`. Backend dates are grouped in UTC
 * (see profile.py), so this builds the grid in UTC too to stay aligned.
 */
export function buildActivityWeeks(
  counts: Record<string, number>,
  weeks: number,
  todayMs: number,
): ActivityDay[][] {
  const todayDow = new Date(todayMs).getUTCDay(); // 0 (Sun) - 6 (Sat)
  const totalCells = weeks * 7;
  const startMs = todayMs - ((weeks - 1) * 7 + todayDow) * DAY_MS;

  const days: ActivityDay[] = [];
  for (let i = 0; i < totalCells; i++) {
    const ms = startMs + i * DAY_MS;
    const inRange = ms <= todayMs;
    const date = isoDateUtc(ms);
    const count = inRange ? (counts[date] ?? 0) : 0;
    days.push({ date, count, level: inRange ? levelFor(count) : 0, inRange });
  }

  const result: ActivityDay[][] = [];
  for (let w = 0; w < weeks; w++) result.push(days.slice(w * 7, w * 7 + 7));
  return result;
}

/** Sum of counts across every cell actually shown in the grid. */
export function totalInGrid(weeks: ActivityDay[][]): number {
  return weeks.reduce((sum, week) => sum + week.reduce((s, d) => s + (d.inRange ? d.count : 0), 0), 0);
}

export interface MonthGroup {
  label: string; // e.g. "Jan"
  weeks: ActivityDay[][];
}

/**
 * Groups consecutive week-columns by the UTC month of their first day, so the
 * heatmap can render one label per month with a visual gap between months.
 */
export function groupWeeksByMonth(weeks: ActivityDay[][]): MonthGroup[] {
  const groups: (MonthGroup & { key: string })[] = [];
  for (const week of weeks) {
    const firstDay = week[0];
    const key = firstDay.date.slice(0, 7); // YYYY-MM
    const last = groups[groups.length - 1];
    if (last && last.key === key) {
      last.weeks.push(week);
    } else {
      const label = new Date(`${firstDay.date}T00:00:00Z`).toLocaleDateString(undefined, {
        month: "short",
        timeZone: "UTC",
      });
      groups.push({ key, label, weeks: [week] });
    }
  }
  return groups.map(({ label, weeks }) => ({ label, weeks }));
}
