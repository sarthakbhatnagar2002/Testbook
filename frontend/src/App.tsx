import { Navigate, Route, Routes } from "react-router-dom";
import Nav from "./components/Nav";
import RequireAuth from "./components/RequireAuth";
import { useAuth } from "./context/AuthContext";
import ChapterQuestionsPage from "./pages/ChapterQuestionsPage";
import ChaptersPage from "./pages/ChaptersPage";
import LoginPage from "./pages/LoginPage";
import PracticeQuestionPage from "./pages/PracticeQuestionPage";
import ProfilePage from "./pages/ProfilePage";
import RegisterPage from "./pages/RegisterPage";
import SubjectsPage from "./pages/SubjectsPage";

function Home() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to="/subjects" replace />;
}

function WithNav() {
  return (
    <>
      <Nav />
      <Routes>
        <Route element={<RequireAuth />}>
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/subjects" element={<SubjectsPage />} />
          <Route path="/subjects/:subjectId" element={<ChaptersPage />} />
          <Route path="/subjects/:subjectId/chapters/:chapterId" element={<ChapterQuestionsPage />} />
          <Route
            path="/subjects/:subjectId/chapters/:chapterId/practice/:questionId"
            element={<PracticeQuestionPage />}
          />
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
      <Route element={<RequireAuth />}>
        <Route path="/" element={<Home />} />
      </Route>
      <Route path="/*" element={<WithNav />} />
    </Routes>
  );
}
