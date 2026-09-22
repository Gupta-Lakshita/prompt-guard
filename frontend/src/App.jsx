import { NavLink, Route, Routes } from "react-router-dom";
import ScannerPage from "./pages/ScannerPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";

function NavItem({ to, children }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `rounded-md px-3 py-1.5 text-sm transition-colors ${
          isActive ? "bg-ink-800 text-text-primary" : "text-text-muted hover:text-text-primary"
        }`
      }
    >
      {children}
    </NavLink>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-ink-950">
      <nav className="border-b border-ink-700 bg-ink-950/95 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3.5">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-accent" aria-hidden="true" />
            <span className="font-mono text-sm font-semibold text-text-primary">Prompt Guard</span>
          </div>
          <div className="flex gap-1">
            <NavItem to="/">Scanner</NavItem>
            <NavItem to="/dashboard">Dashboard</NavItem>
          </div>
        </div>
      </nav>

      <main>
        <Routes>
          <Route path="/" element={<ScannerPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </main>
    </div>
  );
}
