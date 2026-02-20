import { BrowserRouter, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import AnalysisPage from './pages/AnalysisPage';
import WorkspacesPage from './pages/WorkspacesPage';
import Sidebar from './components/Sidebar';
import StatusFooter from './components/StatusFooter';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="main-layout dark-theme">
        <Sidebar />
        <main className="content">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/analysis/:jobId" element={<AnalysisPage />} />
            <Route path="/workspaces" element={<WorkspacesPage />} />
          </Routes>
          <StatusFooter />
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
