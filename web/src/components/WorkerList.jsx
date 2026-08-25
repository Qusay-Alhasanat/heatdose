import { useState, useEffect } from "react";
import { getWorkers } from "../api/client";

const RISK_VAR = {
    low: "var(--risk-low)",
    moderate: "var(--risk-moderate)",
    high: "var(--risk-high)",
    extreme: "var(--risk-extreme)",
};

export default function WorkerList() {
    const [workers, setWorkers] = useState([]);

    useEffect(() => {
        getWorkers().then(setWorkers);
    }, []);

    return (
        <div className="panel">
            <h3 style={{ marginBottom: "14px", fontSize: "15px" }}>
                Workers ({workers.length})
            </h3>
            {workers.map((w) => (
                <div className="worker-row" key={w.worker_id}>
                    <div
                        className="risk-chip"
                        style={{ background: RISK_VAR[w.risk_level] }}
                    />
                    <span className="worker-id">{w.worker_id}</span>
                    <span
                        className="risk-label"
                        style={{
                            color: RISK_VAR[w.risk_level],
                            background: "rgba(255,255,255,0.05)",
                        }}
                    >
                        {w.risk_level}
                    </span>
                    <span className="worker-dose figure">{w.excess_dose}</span>
                </div>
            ))}
        </div>
    );
}