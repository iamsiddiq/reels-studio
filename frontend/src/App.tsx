import { Route, Routes } from 'react-router-dom';

import AppLayout from '@/components/layout/AppLayout';
import ClipDetailPage from '@/pages/ClipDetailPage';
import DashboardPage from '@/pages/DashboardPage';
import LandingPage from '@/pages/LandingPage';
import LibraryPage from '@/pages/LibraryPage';
import NewVideoPage from '@/pages/NewVideoPage';
import ProcessingPage from '@/pages/ProcessingPage';

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/new" element={<NewVideoPage />} />
        <Route path="/processing/:videoId" element={<ProcessingPage />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/clips/:id" element={<ClipDetailPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
      </Route>
    </Routes>
  );
}
