import { useState, useEffect } from "react";
import { getComparison } from "../api/client";

const RISK_VAR = {
    low: "var(--risk-low)",
    moderate: "var(--risk-moderate)",
    high: "var(--risk-high)",
    extreme: "var(--risk-extreme)",
};

const FILTERS = ["all", "extreme", "high", "moderate", "low"];

export default function ComparisonView() {
    const [summary, setSummary] = useState(null);
    const [filter, setFilter] = useState("all");

    useEffect(() => {
        getComparison().then(setSummary);
    }, []);

    if (!summary) return <div className="panel">Loading comparison...</div>;

    const percent = Math.round(
        (summary.underestimated_count / summary.total_workers) * 100
    );

    const rows = Object.values(summary.comparisons)
        .filter((c) => filter === "all" || c.hyperlocal.risk_level === filter)
        .sort((a, b) => b.dose_difference - a.dose_difference);

    return (
        <>
            <div className="panel headline">
                <div className="headline-number figure">
                    {summary.underestimated_count} / {summary.total_workers}
                </div>
                <p className="headline-caption">
                    workers ({percent}%) had their risk underestimated by a single
                    morning weather check — continuous hyperlocal tracking caught
                    what a one-time check missed.
                </p>
            </div>

            <div className="panel">
                <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
                    {FILTERS.map((f) => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={`tab ${filter === f ? "active" : ""}`}
                            style={{ textTransform: "capitalize" }}
                        >
                            {f}
                        </button>
                    ))}
                </div>

                <table>
                    <thead>
                        <tr>
                            <th>Worker</th>
                            <th>Single Morning Check</th>
                            <th>Continuous Tracking</th>
                            <th>Difference</th>
                            <th>Missed?</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((c) => (
                            <tr
                                key={c.worker_id}
                                className={c.risk_underestimated ? "underestimated" : ""}
                            >
                                <td className="figure">{c.worker_id}</td>
                                <td style={{ color: RISK_VAR[c.city_level.risk_level] }}>
                                    {c.city_level.risk_level}{" "}
                                    <span className="figure">({c.city_level.excess_dose})</span>
                                </td>
                                <td style={{ color: RISK_VAR[c.hyperlocal.risk_level] }}>
                                    {c.hyperlocal.risk_level}{" "}
                                    <span className="figure">
                                        ({c.hyperlocal.excess_dose})
                                    </span>
                                </td>
                                <td className="figure">+{c.dose_difference}</td>
                                <td
                                    className={
                                        c.risk_underestimated ? "missed-yes" : "missed-no"
                                    }
                                >
                                    {c.risk_underestimated ? "Yes" : "No"}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                {rows.length === 0 && (
                    <p style={{ color: "var(--text-muted)", fontSize: "13px" }}>
                        No workers in this risk band.
                    </p>
                )}
            </div>
        </>
    );
}