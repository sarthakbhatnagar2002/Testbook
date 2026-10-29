import { describe, expect, it } from "vitest";
import { filterQuestions } from "./questionFilter";
import type { QuestionListItem } from "./types";

const questions: QuestionListItem[] = [
  { id: "1", text: "Q1", image_url: null, status: "not_attempted" },
  { id: "2", text: "Q2", image_url: null, status: "correct" },
  { id: "3", text: "Q3", image_url: null, status: "incorrect" },
  { id: "4", text: "Q4", image_url: null, status: "correct" },
];

describe("filterQuestions", () => {
  it("returns everything for 'all'", () => {
    expect(filterQuestions(questions, "all")).toHaveLength(4);
  });

  it("returns only unattempted questions for 'unsolved'", () => {
    expect(filterQuestions(questions, "unsolved").map((q) => q.id)).toEqual(["1"]);
  });

  it("returns only correctly solved questions for 'solved'", () => {
    expect(filterQuestions(questions, "solved").map((q) => q.id)).toEqual(["2", "4"]);
  });

  it("returns only incorrectly answered questions for 'incorrect'", () => {
    expect(filterQuestions(questions, "incorrect").map((q) => q.id)).toEqual(["3"]);
  });

  it("handles an empty list", () => {
    expect(filterQuestions([], "all")).toEqual([]);
  });
});
