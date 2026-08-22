// web/src/components/ComparisonView.jsx
import { useState, useEffect } from "react";
import { getComparison } from "../api/client";

const RISK_COLORS = {
    low: "#4ade80",
    moderate: "#facc15",
    high: "#fb923c",
    extreme: "#ef4444",
};

export default function ComparisonView() {
    const [summary, setSummary] = useState(null);

    useEffect(() => {
        getComparison().then(setSummary);
    }, []);

    if (!summary) return <p>Loading comparison...</p>;

    const percent = Math.round(
        (summary.underestimated_count / summary.total_workers) * 100
    );

    return (
        <div style={{ padding: "20px" }}>
            {/* الرقم العنوان — لحظة الـpitch */}
            <div
                style={{
                    background: "#1e1e2e",
                    padding: "24px",
                    borderRadius: "8px",
                    marginBottom: "20px",
                    textAlign: "center",
                }}
            >
                <h1 style={{ margin: 0, color: "#ef4444" }}>
                    {summary.underestimated_count} of {summary.total_workers} workers
                    ({percent}%)
                </h1>
                <p style={{ color: "#aaa", marginTop: "8px" }}>
                    had their risk underestimated by a single morning weather check —
                    continuous hyperlocal tracking caught what a one-time check missed
                </p>
            </div>

            {/* جدول المقارنة لكل عامل */}
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                    <tr style={{ textAlign: "left", borderBottom: "2px solid #444" }}>
                        <th style={{ padding: "8px" }}>Worker</th>
                        <th style={{ padding: "8px" }}>Single Morning Check</th>
                        <th style={{ padding: "8px" }}>Continuous Tracking</th>
                        <th style={{ padding: "8px" }}>Difference</th>
                        <th style={{ padding: "8px" }}>Missed?</th>
                    </tr>
                </thead>
                <tbody>
                    {Object.values(summary.comparisons)
                        .sort((a, b) => b.dose_difference - a.dose_difference)
                        .map((c) => (
                            <tr
                                key={c.worker_id}
                                style={{
                                    borderBottom: "1px solid #333",
                                    background: c.risk_underestimated
                                        ? "rgba(239,68,68,0.08)"
                                        : "transparent",
                                }}
                            >
                                <td style={{ padding: "8px" }}>{c.worker_id}</td>
                                <td style={{ padding: "8px", color: RISK_COLORS[c.city_level.risk_level] }}>
                                    {c.city_level.risk_level} ({c.city_level.excess_dose})
                                </td>
                                <td style={{ padding: "8px", color: RISK_COLORS[c.hyperlocal.risk_level] }}>
                                    {c.hyperlocal.risk_level} ({c.hyperlocal.excess_dose})
                                </td>
                                <td style={{ padding: "8px" }}>+{c.dose_difference}</td>
                                <td style={{ padding: "8px" }}>
                                    {c.risk_underestimated ? "⚠️ YES" : "no"}
                                </td>
                            </tr>
                        ))}
                </tbody>
            </table>
        </div>
    );
}