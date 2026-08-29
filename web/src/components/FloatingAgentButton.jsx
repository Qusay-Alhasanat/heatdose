import { useState } from "react";
import AgentPanel from "./AgentPanel";

export default function FloatingAgentButton() {
    const [open, setOpen] = useState(false);

    return (
        <>
            <div className={`agent-launcher ${open ? "is-open" : ""}`}>
                {!open && (
                    <button
                        type="button"
                        className="agent-speech"
                        onClick={() => setOpen(true)}
                        aria-label="Ask the operations assistant"
                    >
                        ASK ME...
                    </button>
                )}
                <button
                    className="agent-trigger"
                    onClick={() => setOpen((o) => !o)}
                    aria-label={open ? "Close operations assistant" : "Ask the operations assistant"}
                    aria-expanded={open}
                >
                    <span className="bot-antenna" aria-hidden="true" />
                    <span className="bot-head" aria-hidden="true">
                        <span className="bot-ear bot-ear-left" />
                        <span className="bot-ear bot-ear-right" />
                        <span className="bot-eye bot-eye-left" />
                        <span className="bot-eye bot-eye-right" />
                        <span className="bot-mouth">{open ? "X" : "_"}</span>
                    </span>
                </button>
            </div>

            {open && (
                <div className="agent-panel-dock">
                    <AgentPanel />
                </div>
            )}
        </>
    );
}