// web/src/api/client.js
const BASE_URL = "https://heatdose-production.up.railway.app";

export async function getWorkers() {
    const res = await fetch(`${BASE_URL}/api/workers`);
    return res.json();
}