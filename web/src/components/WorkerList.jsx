// web/src/components/WorkerList.jsx
import { useState, useEffect } from "react";
import { getWorkers } from "../Api/client";

const RISK_COLORS = {
    low: "#4ade80",
    moderate: "#facc15",
    high: "#fb923c",
    extreme: "#ef4444",
};

export default function WorkerList() {
    const [workers, setWorkers] = useState([]);

    useEffect(() => {
        getWorkers().then(setWorkers);
    }, []);

    return (
        <div>
            <h2>Workers</h2>
            {workers.map((w) => (
                <div
                    key={w.worker_id}
                    style={{
                        padding: "8px",
                        marginBottom: "4px",
                        borderLeft: `6px solid ${RISK_COLORS[w.risk_level]}`,
                    }}
                >
                    {w.worker_id} — {w.risk_level} — excess dose: {w.excess_dose}
                </div>
            ))}
        </div>
    );
}