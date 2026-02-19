import { BrowserRouter, Routes, Route } from 'react-router-dom';
import DashboardHome from './pages/DashboardHome';
import WorkspacePage from './pages/WorkspacePage';
import AnalyticsPage from './pages/AnalyticsPage';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Routes>
          <Route path="/" element={<DashboardHome />} />
          <Route path="/workspace/:workspaceId" element={<WorkspacePage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
