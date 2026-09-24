import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { AuthProvider } from './context/AuthContext';
import AppShell from './components/layout/AppShell';
import ProtectedRoute from './components/auth/ProtectedRoute';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Dashboard from './pages/Dashboard';
import Knowledge from './pages/Knowledge';
import Courses from './pages/Courses';
import Assessment from './pages/Assessment';
import Planner from './pages/Planner';
import Assistant from './pages/Assistant';
import Progress from './pages/Progress';
import Settings from './pages/Settings';
import HelpSupport from './pages/HelpSupport';
import Profile from './pages/Profile';

export default function App() {
  return (
    <AppProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<AppShell />}>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/knowledge" element={<Knowledge />} />
                <Route path="/courses" element={<Courses />} />
                <Route path="/assessment" element={<Assessment />} />
                <Route path="/planner" element={<Planner />} />
                <Route path="/assistant" element={<Assistant />} />
                <Route path="/progress" element={<Progress />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/help" element={<HelpSupport />} />
                <Route path="/profile" element={<Profile />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </AppProvider>
  );
}
