import { buildActivityWeeks, groupWeeksByMonth, totalInGrid, type ActivityDay } from "../lib/activityGrid";

const WEEKS = 53;

const LEVEL_CLASSES: Record<ActivityDay["level"], string> = {
  0: "bg-gray-800",
  1: "bg-emerald-900",
  2: "bg-emerald-700",
  3: "bg-emerald-500",
  4: "bg-emerald-300",
};

function formatDate(iso: string): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

export default function ActivityHeatmap({ counts }: { counts: Record<string, number> }) {
  const weeks = buildActivityWeeks(counts, WEEKS, Date.now());
  const total = totalInGrid(weeks);
  const months = groupWeeksByMonth(weeks);

  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-900 p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-400">Activity</h2>
        <span className="text-xs text-gray-400">{total} questions solved in the last year</span>
      </div>

      <div className="overflow-x-auto pb-1">
        <div className="flex items-start gap-3" style={{ width: "max-content" }}>
          {months.map((month, mi) => (
            <div key={mi} className="flex flex-col">
              <span className="mb-1 block text-[11px] text-gray-500">{month.label}</span>
              <div className="flex gap-[3px]">
                {month.weeks.map((week, wi) => (
                  <div key={wi} className="flex flex-col gap-[3px]">
                    {week.map((day) =>
                      day.inRange ? (
                        <div
                          key={day.date}
                          title={`${day.count} solved on ${formatDate(day.date)}`}
                          className={`h-[11px] w-[11px] rounded-sm ${LEVEL_CLASSES[day.level]}`}
                        />
                      ) : (
                        <div key={day.date} className="h-[11px] w-[11px] rounded-sm bg-transparent" />
                      ),
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-3 flex items-center justify-end gap-1.5 text-xs text-gray-500">
        <span>Less</span>
        {([0, 1, 2, 3, 4] as const).map((level) => (
          <div key={level} className={`h-[11px] w-[11px] rounded-sm ${LEVEL_CLASSES[level]}`} />
        ))}
        <span>More</span>
      </div>
    </div>
  );
}
