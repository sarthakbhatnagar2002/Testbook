// Mirrors backend/app/schemas.py. The API uses snake_case field names and
// serializes datetimes as ISO-8601 strings with an explicit UTC offset.

export type Role = "teacher" | "student";
export type Rating = "easy" | "medium" | "hard";

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
}

export interface Option {
  id: string;
  text: string;
  image_url: string | null;
  position: number;
}

export interface OptionWithAnswer extends Option {
  is_correct: boolean;
}

export interface Question {
  id: string;
  text: string;
  image_url: string | null;
  explanation: string | null;
  teacher_rating: Rating;
  attempts_count: number;
  correct_count: number;
  tier: Rating;
  tier_source: "data" | "teacher";
  options: OptionWithAnswer[];
  created_at: string;
}

export interface QuestionPublic {
  id: string;
  text: string;
  image_url: string | null;
  options: Option[];
}

export interface TestSection {
  id: string;
  title: string;
  position: number;
  duration_mins: number;
  question_count: number;
}

export interface Test {
  id: string;
  title: string;
  room_key: string;
  total_duration_mins: number;
  marks_correct: number;
  marks_wrong: number;
  marks_skipped: number;
  published: boolean;
  archived: boolean;
  start_time: string | null;
  end_time: string | null;
  sections: TestSection[];
  created_at: string;
}

export interface StudentTest {
  id: string;
  title: string;
  total_duration_mins: number;
  marks_correct: number;
  marks_wrong: number;
  marks_skipped: number;
  start_time: string | null;
  end_time: string | null;
  availability: "upcoming" | "open" | "closed";
  attempt_status: "none" | "in_progress" | "submitted";
  attempt_id: string | null;
}

export interface PreviousAttempt {
  attempt_id: string;
  test_id: string;
  test_title: string;
  score: number;
  correct_count: number;
  wrong_count: number;
  skipped_count: number;
  submitted_at: string | null;
}

export interface QuestionState {
  selected_option_id: string | null;
  visited: boolean;
  marked_for_review: boolean;
  time_spent_seconds: number;
}

export interface SectionState {
  started_at: string | null;
  locked: boolean;
}

export interface DraftState {
  current_question_id: string | null;
  questions: Record<string, QuestionState>;
  sections: Record<string, SectionState>;
}

export interface AttemptSection {
  id: string;
  title: string;
  position: number;
  duration_mins: number;
  questions: QuestionPublic[];
}

export interface AttemptState {
  attempt_id: string;
  test_id: string;
  test_title: string;
  marks_correct: number;
  marks_wrong: number;
  marks_skipped: number;
  started_at: string;
  total_seconds_remaining: number;
  status: "in_progress" | "submitted";
  sections: AttemptSection[];
  draft: DraftState;
}

export interface ReviewAnswer {
  question: {
    id: string;
    text: string;
    image_url: string | null;
    explanation: string | null;
    options: OptionWithAnswer[];
  };
  selected_option_id: string | null;
  is_correct: boolean;
}

export interface AttemptResult {
  attempt_id: string;
  test_title: string;
  score: number;
  correct_count: number;
  wrong_count: number;
  skipped_count: number;
  marks_correct: number;
  marks_wrong: number;
  marks_skipped: number;
  submitted_at: string | null;
  answers: ReviewAnswer[];
}

export interface RecentScore {
  test_title: string;
  score: number;
  submitted_at: string | null;
}

export interface Profile {
  name: string;
  email: string;
  role: Role;
  tests_taken: number;
  average_score: number;
  overall_accuracy: number;
  recent_scores: RecentScore[];
}

export interface TeacherAttemptRow {
  user_name: string;
  user_email: string;
  score: number;
  correct_count: number;
  wrong_count: number;
  skipped_count: number;
  submitted_at: string | null;
}

export interface TeacherTestResults {
  test_id: string;
  title: string;
  attempt_count: number;
  average_score: number;
  highest_score: number;
  attempts: TeacherAttemptRow[];
}
