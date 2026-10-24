export type TileStatus = "not_visited" | "answered" | "not_answered" | "marked" | "marked_and_answered";

export interface QuestionProgress {
  visited: boolean;
  selectedOptionId: string | null;
  markedForReview: boolean;
}

/**
 * Pure derivation of a palette tile's status from a question's progress.
 * Not visited is tracked separately from not answered (white vs red) so a
 * student can always see which questions they haven't opened yet.
 */
export function deriveTileStatus({ visited, selectedOptionId, markedForReview }: QuestionProgress): TileStatus {
  if (!visited) return "not_visited";
  const answered = selectedOptionId !== null && selectedOptionId !== undefined && selectedOptionId !== "";
  if (markedForReview) return answered ? "marked_and_answered" : "marked";
  return answered ? "answered" : "not_answered";
}

export function countByStatus(progress: QuestionProgress[]): Record<TileStatus, number> {
  const counts: Record<TileStatus, number> = {
    not_visited: 0,
    answered: 0,
    not_answered: 0,
    marked: 0,
    marked_and_answered: 0,
  };
  for (const p of progress) {
    counts[deriveTileStatus(p)]++;
  }
  return counts;
}
