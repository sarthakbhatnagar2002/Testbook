import { describe, expect, it } from "vitest";
import { buildActivityWeeks, groupWeeksByMonth, totalInGrid } from "./activityGrid";

// A Wednesday, for a predictable "today".
const WEDNESDAY = Date.UTC(2026, 0, 14); // 2026-01-14 is a Wednesday (UTC)

describe("buildActivityWeeks", () => {
  it("produces `weeks` columns of 7 days each", () => {
    const grid = buildActivityWeeks({}, 4, WEDNESDAY);
    expect(grid).toHaveLength(4);
    grid.forEach((week) => expect(week).toHaveLength(7));
  });

  it("places today in the last column at the correct weekday row", () => {
    const grid = buildActivityWeeks({}, 3, WEDNESDAY);
    const lastWeek = grid[grid.length - 1];
    // Wednesday is index 3 (Sun=0 ... Wed=3).
    expect(lastWeek[3].date).toBe("2026-01-14");
    expect(lastWeek[3].inRange).toBe(true);
  });

  it("marks days after today as out of range", () => {
    const grid = buildActivityWeeks({}, 1, WEDNESDAY);
    const week = grid[0];
    // Thu, Fri, Sat (indices 4,5,6) are after Wednesday.
    expect(week[4].inRange).toBe(false);
    expect(week[5].inRange).toBe(false);
    expect(week[6].inRange).toBe(false);
    // Sun..Wed (0..3) are on or before today.
    expect(week[0].inRange).toBe(true);
    expect(week[3].inRange).toBe(true);
  });

  it("looks up counts by date and computes a level", () => {
    const grid = buildActivityWeeks({ "2026-01-14": 7 }, 1, WEDNESDAY);
    const today = grid[0][3];
    expect(today.count).toBe(7);
    expect(today.level).toBe(3);
  });

  it("gives a zero count and level 0 for days with no data", () => {
    const grid = buildActivityWeeks({}, 1, WEDNESDAY);
    expect(grid[0][0].count).toBe(0);
    expect(grid[0][0].level).toBe(0);
  });

  it("never attributes counts to out-of-range future days", () => {
    const grid = buildActivityWeeks({ "2026-01-16": 5 }, 1, WEDNESDAY);
    // 2026-01-16 is Friday, after "today" (Wednesday) -- must not leak in.
    const friday = grid[0][5];
    expect(friday.date).toBe("2026-01-16");
    expect(friday.count).toBe(0);
    expect(friday.inRange).toBe(false);
  });
});

describe("totalInGrid", () => {
  it("sums counts across all in-range cells only", () => {
    const grid = buildActivityWeeks({ "2026-01-12": 2, "2026-01-14": 3, "2026-01-16": 99 }, 1, WEDNESDAY);
    // 2026-01-16 is out of range (future), so its count must not be included
    // even though it isn't in the input map's keys that matter here.
    expect(totalInGrid(grid)).toBe(5);
  });

  it("is zero for an empty grid", () => {
    expect(totalInGrid(buildActivityWeeks({}, 2, WEDNESDAY))).toBe(0);
  });
});

describe("groupWeeksByMonth", () => {
  it("keeps weeks from the same month in one group", () => {
    // 2026-01-14 is a Wednesday; the 2 weeks ending on it (Jan 4 - Jan 17)
    // both start within January.
    const grid = buildActivityWeeks({}, 2, WEDNESDAY);
    const groups = groupWeeksByMonth(grid);
    expect(groups).toHaveLength(1);
    expect(groups[0].label).toBe("Jan");
    expect(groups[0].weeks).toHaveLength(2);
  });

  it("starts a new group when the week's first day crosses into a new month", () => {
    // 2026-01-14 is a Wednesday; 3 weeks back crosses into December 2025
    // (week columns start Dec 28 and Jan 4/11).
    const grid = buildActivityWeeks({}, 3, WEDNESDAY);
    const groups = groupWeeksByMonth(grid);
    expect(groups.length).toBeGreaterThan(1);
    expect(groups[0].label).toBe("Dec");
    expect(groups[groups.length - 1].label).toBe("Jan");
  });

  it("every week from the input appears in exactly one group", () => {
    const grid = buildActivityWeeks({}, 12, WEDNESDAY);
    const groups = groupWeeksByMonth(grid);
    const totalWeeks = groups.reduce((sum, g) => sum + g.weeks.length, 0);
    expect(totalWeeks).toBe(grid.length);
  });
});
