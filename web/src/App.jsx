import { useState } from "react";
import MapView from "./components/MapView";
import WorkerList from "./components/WorkerList";
import ComparisonView from "./components/ComparisonView";
import ThermalScale from "./components/ThermalScale";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "comparison", label: "Impact" },
];

function App() {
  const [tab, setTab] = useState("dashboard");

  return (
    <div>
      <div className="topbar">
        <div className="brand">
          <span className="live-dot" />
          <span className="brand-name">HeatDose</span>
        </div>
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
    </div>
  );
}

export default App;