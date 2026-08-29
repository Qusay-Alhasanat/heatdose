# agent/ — HeatDose Agent Layer

LLM-powered agent that answers an operations manager's questions about
worker heat risk by calling four tools backed by `data/`. Provider:
OpenAI (`gpt-4o-mini` for dev, per `Agent_Brief.md` section 0.5).

## Files

| File | Purpose |
| --- | --- |
| `tools.py` | The four tools (`get_worker_status`, `list_workers_at_risk`, `find_cool_point`, `compare_to_city_baseline`), their OpenAI function-calling schemas, and `call_tool()` dispatch. Wraps `data/` only — never talks to `fortyguard_client.py` or the FortyGuard API. |
| `prompts.py` | The system prompt: role, guardrails, and the cool-point-unreachable behavior (see below). |
| `core.py` | `run_agent(question) -> (answer, tool_trace)` — the tool-calling loop, with the step limit, timeout, and tracing enforced in code. |

## Setup

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini   # optional, this is the default
```

Add these to `.env` (already gitignored) for local runs, and to the
Railway project's environment variables for the deployed API — `core.py`
reads them from `os.environ`, and `.env` is only loaded locally via
`load_dotenv()`. `openai` was added to `pyproject.toml`'s dependencies —
run `uv sync` (or `pip install -e .`) to pick it up.

Note: an earlier commit briefly switched this file to OpenRouter; that
was reverted (29 Aug) so the code, this README, and `PROJECT_SPEC.md`'s
confirmed decision all agree on OpenAI, direct.

## Try it

No web/API layer needed — this runs standalone:

```
uv run python agent/core.py "who should I pull off the job right now?"
uv run python agent/core.py "is there anywhere cooler for W-01 to go?"
uv run python agent/tools.py   # exercises all four tools directly, no LLM call, no API key needed
```

## Guardrails (PROJECT_SPEC.md §7 / Agent_Brief.md §3) — enforced in code, not just prompted

- **Step limit: 5 tool calls per query.** `core.py` counts real tool
  executions and hard-stops at 5 — the model gets one final tool-free
  turn to summarize whatever it already gathered rather than a bare
  canned string.
- **Timeout: 30s wall-clock per query.** Checked before every model
  call; the remaining budget is also passed as the per-call timeout so
  a single slow call can't blow past it.
- **No fabrication.** System prompt rule 1. A tool result with an
  `"error"` key is explicitly *not* data to report (rule 2) — every
  wrapper in `tools.py` catches `data/`'s documented exceptions
  (`UnknownWorkerError`, `MissingRealDataError`, bad `min_level`) and
  returns a structured error dict instead of letting them propagate as
  raw exceptions into the LLM's context.
- **No medical claims.** System prompt rule 3 — operational actions
  only (rest, rotation, rescheduling, stop work).
- **Full tracing.** Every tool call actually executed is recorded as
  `{"tool", "args", "result"}` — the exact shape `api/models.py`'s
  `ToolTraceEntry` expects — and returned alongside the answer.

## Open decision, now closed: cool point unreachable

When `find_cool_point` reports `"reachable": false`, the system prompt
(rule 4) has the agent:

1. **Default:** recommend on-site rest and reduced work intensity.
2. **Escalate when `risk_level == "extreme"`:** recommend stopping that
   worker's work now, since no shelter is reachable and continuing is
   the higher-risk option than stopping.

This is Option 1 (default) layered with Option 2 (extreme-risk
escalation) from `PROJECT_SPEC.md` §7 / `Agent_Brief.md` §4 — the
combination the spec itself recommended as most defensible. Reasoning:
a worker in an exposed industrial yard genuinely may have nowhere
better to go (confirmed by `data/cool_points.py`'s own design doc —
zone centres are km apart, candidate points are hand-placed close to
hot zones, and even so several workers have no candidate both ≥3°C
cooler and ≤800m away). Recommending a "shelter" that costs more heat
exposure to reach than it saves would be worse than doing nothing.
But leaving an extreme-risk worker on-site indefinitely with no escape
plan is its own hazard, so that specific combination — extreme risk
*and* nowhere to go — is the one case that escalates past "rest in
place" to "stop work."

Verified in the current cached dataset: `W-01` is exactly this case
(`risk_level: "extreme"`, `find_cool_point` reachable: false) — a real
example to use in the demo, not a hypothetical.

## Integration into `api/`

Not done here deliberately — `api/main.py` is Qusay's file, and the
brief (`Agent_Brief.md` §0) describes the swap as a single function
body:

```python
@app.post("/api/agent/query", response_model=AgentQueryResponse)
def agent_query(request: AgentQueryRequest) -> AgentQueryResponse:
    from agent.core import run_agent
    answer, trace = run_agent(request.question)
    return AgentQueryResponse(
        answer=answer,
        tool_trace=[
            ToolTraceEntry(tool=t["tool"], args=t["args"], result=t["result"])
            for t in trace
        ],
    )
```

`run_agent()`'s return shape is already exactly what `AgentQueryResponse`
needs — no changes to `api/models.py` required.

## Tests

`tests/test_agent_tools.py` — the four tool wrappers against real
cached data (no OpenAI key needed, no network).
`tests/test_agent_core.py` — the tool-calling loop's mechanics (dispatch,
tracing, the 5-call step limit) against a scripted fake OpenAI client,
so the guardrails are verified by a test, not just manual inspection.

```
uv run pytest tests/test_agent_tools.py tests/test_agent_core.py -v
```
