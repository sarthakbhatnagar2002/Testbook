import { describe, expect, it } from "vitest";
import { timeAgo } from "./timeAgo";

describe("timeAgo", () => {
  const now = new Date("2026-01-10T12:00:00Z").getTime();

  it("shows 'just now' for very recent timestamps", () => {
    expect(timeAgo("2026-01-10T11:59:50Z", now)).toBe("just now");
  });

  it("shows minutes", () => {
    expect(timeAgo("2026-01-10T11:45:00Z", now)).toBe("15m ago");
  });

  it("shows hours", () => {
    expect(timeAgo("2026-01-10T09:00:00Z", now)).toBe("3h ago");
  });

  it("shows days", () => {
    expect(timeAgo("2026-01-07T12:00:00Z", now)).toBe("3d ago");
  });

  it("never goes negative for a future timestamp", () => {
    expect(timeAgo("2026-01-11T12:00:00Z", now)).toBe("just now");
  });
});
