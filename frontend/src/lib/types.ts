// Mirrors backend/app/schemas.py. The API uses snake_case field names and
// serializes datetimes as ISO-8601 strings with an explicit UTC offset.

export interface User {
  id: string;
  name: string;
  email: string;
}

export interface Subject {
  id: string;
  name: string;
  question_count: number;
  solved_count: number;
  accuracy: number;
}

export interface Option {
  id: string;
  text: string;
  image_url: string | null;
  position: number;
}

export type QuestionStatus = "not_attempted" | "correct" | "incorrect";

export interface QuestionListItem {
  id: string;
  text: string;
  image_url: string | null;
  status: QuestionStatus;
}

export interface QuestionPractice {
  id: string;
  subject_id: string;
  subject_name: string;
  text: string;
  image_url: string | null;
  options: Option[];
  status: QuestionStatus;
  next_question_id: string | null;
  prev_question_id: string | null;
}

export interface AnswerResult {
  is_correct: boolean;
  correct_option_id: string;
  selected_option_id: string;
  explanation: string | null;
}

export interface SubjectProgress {
  subject_id: string;
  subject_name: string;
  total_questions: number;
  solved_count: number;
  accuracy: number;
  last_practiced_at: string | null;
}

export interface RecentAttempt {
  question_id: string;
  question_text: string;
  subject_name: string;
  is_correct: boolean;
  created_at: string;
}

export interface Profile {
  name: string;
  email: string;
  total_questions_solved: number;
  total_questions_attempted: number;
  overall_accuracy: number;
  currently_solving: SubjectProgress | null;
  subjects: SubjectProgress[];
  recent_attempts: RecentAttempt[];
}
