import { BrowserRouter, Routes, Route } from "react-router-dom";
import OfficerDashboard from "./OfficerDashboard";
import TicketDetailPage from "./TicketDetailPage";
import CitizenTracker from "./CitizenTracker";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<OfficerDashboard />} />
        <Route path="/ticket/:id" element={<TicketDetailPage />} />
        <Route path="/track" element={<CitizenTracker />} />
      </Routes>
    </BrowserRouter>
  );
}
