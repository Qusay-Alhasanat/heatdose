import { useEffect, useState } from "react";
import MapView from "./components/MapView";
import WorkerList from "./components/WorkerList";
import ComparisonView from "./components/ComparisonView";
import ThermalScale from "./components/ThermalScale";
import FloatingAgentButton from "./components/FloatingAgentButton";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "comparison", label: "Impact" },
];

function App() {
  const [tab, setTab] = useState("dashboard");
  const [theme, setTheme] = useState(() => {
    const savedTheme = window.localStorage.getItem("heatdose-theme");
    if (savedTheme === "light" || savedTheme === "dark") return savedTheme;
    return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("heatdose-theme", theme);
  }, [theme]);

  return (
    <div>
      <div className="topbar">
        <div className="brand">
          <span className="live-dot" />
          <span className="brand-name">HeatDose</span>
        </div>
        <div className="topbar-actions">
          <div className="tabs">
            {TABS.map((t) => (
              <button
                key={t.id}
                className={`tab ${tab === t.id ? "active" : ""}`}
                onClick={() => setTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>
          <button
            className="theme-toggle"
            type="button"
            onClick={() => setTheme((currentTheme) => currentTheme === "dark" ? "light" : "dark")}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            <span className="theme-toggle-icon" aria-hidden="true">
              {theme === "dark" ? "☼" : "☾"}
            </span>
            <span>{theme === "dark" ? "Light" : "Dark"}</span>
          </button>
        </div>
      </div>

      <ThermalScale />

      <div className="page">
        {tab === "dashboard" && (
          <div className="dashboard-grid">
            <MapView />
            <WorkerList />
          </div>
        )}
        {tab === "comparison" && <ComparisonView />}
      </div>

      <FloatingAgentButton />
    </div>
  );
}

export default App;