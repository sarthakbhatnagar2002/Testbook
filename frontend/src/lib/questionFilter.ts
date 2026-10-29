import type { QuestionListItem } from "./types";

export type QuestionFilter = "all" | "unsolved" | "solved" | "incorrect";

/** Pure filter used by the subject question list's filter tabs. */
export function filterQuestions(questions: QuestionListItem[], filter: QuestionFilter): QuestionListItem[] {
  switch (filter) {
    case "solved":
      return questions.filter((q) => q.status === "correct");
    case "unsolved":
      return questions.filter((q) => q.status === "not_attempted");
    case "incorrect":
      return questions.filter((q) => q.status === "incorrect");
    case "all":
    default:
      return questions;
  }
}
