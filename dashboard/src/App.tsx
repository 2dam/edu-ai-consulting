import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { UserProvider } from "./context/UserContext";
import { AdminPage } from "./pages/AdminPage";
import { BoardPage } from "./pages/BoardPage";
import { CommunityHome } from "./pages/CommunityHome";
import { EducationBoard } from "./pages/EducationBoard";
import { NewsDetailPage } from "./pages/NewsDetailPage";
import { NewsFeed } from "./pages/NewsFeed";
import { ParentingBoard } from "./pages/ParentingBoard";
import { PostDetailPage } from "./pages/PostDetailPage";
import { RegionBoard } from "./pages/RegionBoard";

function App() {
  return (
    <UserProvider>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<CommunityHome />} />
          <Route path="/news" element={<NewsFeed />} />
          <Route path="/news/:id" element={<NewsDetailPage />} />
          <Route path="/posts/:id" element={<PostDetailPage />} />
          <Route path="/board/:slug" element={<BoardPage />} />
          <Route path="/mom-cafe/region/:region" element={<RegionBoard />} />
          <Route path="/mom-cafe/education" element={<EducationBoard />} />
          <Route path="/mom-cafe/parenting" element={<ParentingBoard />} />
          <Route path="/admin" element={<AdminPage />} />
        </Route>
      </Routes>
    </UserProvider>
  );
}

export default App;
