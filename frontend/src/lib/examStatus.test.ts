import { describe, expect, it } from "vitest";
import { countByStatus, deriveTileStatus } from "./examStatus";

describe("deriveTileStatus", () => {
  it("is not_visited before the student ever opens the question", () => {
    expect(deriveTileStatus({ visited: false, selectedOptionId: null, markedForReview: false })).toBe(
      "not_visited",
    );
    // Even a (hypothetical) stray selection shouldn't matter before a visit.
    expect(deriveTileStatus({ visited: false, selectedOptionId: "a", markedForReview: false })).toBe(
      "not_visited",
    );
  });

  it("is not_answered once visited with nothing selected", () => {
    expect(deriveTileStatus({ visited: true, selectedOptionId: null, markedForReview: false })).toBe(
      "not_answered",
    );
  });

  it("is answered once visited with a selection", () => {
    expect(deriveTileStatus({ visited: true, selectedOptionId: "a", markedForReview: false })).toBe("answered");
  });

  it("is marked when flagged for review with no answer", () => {
    expect(deriveTileStatus({ visited: true, selectedOptionId: null, markedForReview: true })).toBe("marked");
  });

  it("is marked_and_answered when flagged for review with an answer", () => {
    expect(deriveTileStatus({ visited: true, selectedOptionId: "a", markedForReview: true })).toBe(
      "marked_and_answered",
    );
  });

  it("treats an empty string selection as unanswered", () => {
    expect(deriveTileStatus({ visited: true, selectedOptionId: "", markedForReview: false })).toBe(
      "not_answered",
    );
  });
});

describe("countByStatus", () => {
  it("tallies live counts for the legend", () => {
    const counts = countByStatus([
      { visited: false, selectedOptionId: null, markedForReview: false },
      { visited: true, selectedOptionId: "a", markedForReview: false },
      { visited: true, selectedOptionId: null, markedForReview: false },
      { visited: true, selectedOptionId: null, markedForReview: true },
      { visited: true, selectedOptionId: "a", markedForReview: true },
    ]);
    expect(counts).toEqual({
      not_visited: 1,
      answered: 1,
      not_answered: 1,
      marked: 1,
      marked_and_answered: 1,
    });
  });
});
