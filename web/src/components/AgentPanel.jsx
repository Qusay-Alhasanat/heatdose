import { useState } from "react";
import { askAgent } from "../api/client";

export default function AgentPanel() {
    const [question, setQuestion] = useState("");
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(false);

    const handleAsk = async () => {
        if (!question.trim()) return;
        const userQuestion = question;
        setQuestion("");
        setLoading(true);

        setMessages((prev) => [...prev, { role: "user", text: userQuestion }]);

        try {
            const result = await askAgent(userQuestion);
            setMessages((prev) => [
                ...prev,
                { role: "agent", text: result.answer, trace: result.tool_trace },
            ]);
        } catch (err) {
            setMessages((prev) => [
                ...prev,
                { role: "agent", text: "Error reaching the agent.", trace: [] },
            ]);
        }
        setLoading(false);
    };

    return (
        <div className="panel">
            <h3 style={{ marginBottom: "14px", fontSize: "15px" }}>
                Ask the operations assistant
            </h3>

            <div style={{ marginBottom: "16px" }}>
                {messages.map((m, i) => (
                    <div key={i} style={{ marginBottom: "12px" }}>
                        <div
                            style={{
                                fontSize: "12px",
                                color: "var(--text-muted)",
                                marginBottom: "4px",
                            }}
                        >
                            {m.role === "user" ? "You" : "Agent"}
                        </div>
                        <div>{m.text}</div>

                        {m.trace && m.trace.length > 0 && (
                            <details style={{ marginTop: "8px" }}>
                                <summary
                                    style={{
                                        cursor: "pointer",
                                        fontSize: "12px",
                                        color: "var(--accent-system)",
                                    }}
                                >
                                    {m.trace.length} tool call{m.trace.length > 1 ? "s" : ""}
                                </summary>
                                <div
                                    className="figure"
                                    style={{
                                        fontSize: "12px",
                                        marginTop: "6px",
                                        color: "var(--text-muted)",
                                    }}
                                >
                                    {m.trace.map((t, j) => (
                                        <div key={j} style={{ marginBottom: "4px" }}>
                                            {t.tool}({JSON.stringify(t.args)})
                                        </div>
                                    ))}
                                </div>
                            </details>
                        )}
                    </div>
                ))}
                {loading && (
                    <div style={{ color: "var(--text-muted)", fontSize: "13px" }}>
                        Thinking...
                    </div>
                )}
            </div>

            <div style={{ display: "flex", gap: "8px" }}>
                <input
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAsk()}
                    placeholder="Who should I pull off the job right now?"
                    style={{
                        flex: 1,
                        padding: "10px 12px",
                        background: "var(--bg-panel-raised)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                        color: "var(--text-primary)",
                    }}
                />
                <button
                    onClick={handleAsk}
                    disabled={loading}
                    style={{
                        padding: "10px 18px",
                        background: "var(--accent-system)",
                        border: "none",
                        borderRadius: "8px",
                        color: "#0b0f14",
                        fontWeight: 500,
                        cursor: "pointer",
                    }}
                >
                    Ask
                </button>
            </div>
        </div>
    );
}