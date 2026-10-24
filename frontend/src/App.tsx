import { Navigate, Route, Routes } from "react-router-dom";
import Nav from "./components/Nav";
import RequireAuth from "./components/RequireAuth";
import { useAuth } from "./context/AuthContext";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import ExamPage from "./pages/student/ExamPage";
import ProfilePage from "./pages/student/ProfilePage";
import ResultsPage from "./pages/student/ResultsPage";
import TestsPage from "./pages/student/TestsPage";
import NewTestPage from "./pages/teacher/NewTestPage";
import TeacherTestResultsPage from "./pages/teacher/TeacherTestResultsPage";
import TeacherTestsPage from "./pages/teacher/TeacherTestsPage";

function Home() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "teacher" ? "/teacher/tests" : "/tests"} replace />;
}

function WithNav() {
  return (
    <>
      <Nav />
      <Routes>
        <Route element={<RequireAuth role="student" />}>
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/tests" element={<TestsPage />} />
          <Route path="/tests/results/:attemptId" element={<ResultsPage />} />
        </Route>
        <Route element={<RequireAuth role="teacher" />}>
          <Route path="/teacher/tests" element={<TeacherTestsPage />} />
          <Route path="/teacher/tests/new" element={<NewTestPage />} />
          <Route path="/teacher/tests/:testId/results" element={<TeacherTestResultsPage />} />
        </Route>
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<RequireAuth role="student" />}>
        <Route path="/tests/attempt/:attemptId" element={<ExamPage />} />
      </Route>
      <Route element={<RequireAuth />}>
        <Route path="/" element={<Home />} />
      </Route>
      <Route path="/*" element={<WithNav />} />
    </Routes>
  );
}
