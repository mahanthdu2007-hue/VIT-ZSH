import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { Dashboard } from "./pages/Dashboard";
import { Landing } from "./pages/Landing";
import { NotFound } from "./pages/NotFound";
import { ParentForm } from "./pages/ParentForm";
import { StudentAssessment } from "./pages/StudentAssessment";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Landing />} />
        <Route path="assess/:track" element={<StudentAssessment />} />
        <Route path="assess/:track/parent" element={<ParentForm />} />
        <Route path="dashboard/:id" element={<Dashboard />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
