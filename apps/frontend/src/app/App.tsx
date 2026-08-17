import { NavLink, Route, Routes } from "react-router-dom";

import { HomePage } from "../pages/HomePage";
import { AnalyzePage } from "../pages/AnalyzePage";
import { ComparePage } from "../pages/ComparePage";

export function App() {
  return (
    <div className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">AI Portfolio Project</p>
          <h1>AI Graph Analyzer and Comparator</h1>
        </div>
        <nav className="nav-links" aria-label="Primary">
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/analyze">Analyze Graph</NavLink>
          <NavLink to="/compare">Compare Graphs</NavLink>
        </nav>
      </header>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/analyze" element={<AnalyzePage />} />
          <Route path="/compare" element={<ComparePage />} />
        </Routes>
      </main>
    </div>
  );
}
