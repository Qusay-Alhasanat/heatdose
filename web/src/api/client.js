const BASE_URL = "https://heatdose-production.up.railway.app";

export async function getWorkers() {
    const res = await fetch(`${BASE_URL}/api/workers`);
    return res.json();
}

export async function getComparison() {
    const res = await fetch(`${BASE_URL}/api/comparison`);
    return res.json();
}

export async function askAgent(question) {
    const res = await fetch(`${BASE_URL}/api/agent/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
    });
    return res.json();
}

export async function getCoolPoints(hour) {
    const res = await fetch(`${BASE_URL}/api/cool-points?hour=${hour}`);
    return res.json();
}

export async function getWorkerCoolPoint(workerId) {
    const res = await fetch(`${BASE_URL}/api/workers/${workerId}/cool-point`);
    return res.json();
}