import { useState, useEffect } from "react";
import {
    MapContainer,
    TileLayer,
    CircleMarker,
    Tooltip,
    Polyline,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { getWorkers, getCoolPoints, getWorkerCoolPoint } from "../api/client";

const RISK_HEX = {
    low: "#34d399",
    moderate: "#fbbf24",
    high: "#fb923c",
    extreme: "#f87171",
};

const PHOENIX_CENTER = [33.45, -112.065];
// Fixed hour for the cool-point overlay snapshot — this is a static
// demo (historical cached data, not live), so we pick the afternoon
// peak hour for the clearest picture.
const MAP_HOUR = 14;

export default function MapView() {
    const [workers, setWorkers] = useState([]);
    const [coolPoints, setCoolPoints] = useState([]);
    const [selectedWorker, setSelectedWorker] = useState(null);
    const [route, setRoute] = useState(null);

    useEffect(() => {
        getWorkers().then(setWorkers);
        getCoolPoints(MAP_HOUR).then(setCoolPoints);
    }, []);

    const handleWorkerClick = async (worker) => {
        if (selectedWorker === worker.worker_id) {
            setSelectedWorker(null);
            setRoute(null);
            return;
        }
        setSelectedWorker(worker.worker_id);
        setRoute(null);
        const result = await getWorkerCoolPoint(worker.worker_id);
        setRoute(result);
    };

    const selected = workers.find((w) => w.worker_id === selectedWorker);

    return (
        <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
            <div className="map-container">
                <MapContainer
                    center={PHOENIX_CENTER}
                    zoom={12}
                    style={{ height: "480px", width: "100%" }}
                >
                    <TileLayer
                        attribution="&copy; OpenStreetMap contributors"
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />

                    {/* Cool point candidates - small blue dots. Synthetic
              temperatures (see data/cool_points.py), not real
              FortyGuard data - flagged in the tooltip. */}
                    {coolPoints.map((cp) => (
                        <CircleMarker
                            key={cp.point_id}
                            center={[cp.location.lat, cp.location.lng]}
                            radius={5}
                            pathOptions={{
                                color: "#38bdf8",
                                fillColor: "#38bdf8",
                                fillOpacity: 0.6,
                                weight: 1,
                            }}
                        >
                            <Tooltip>
                                {cp.zone_type} — {cp.temp_c}°C (modelled, not measured)
                            </Tooltip>
                        </CircleMarker>
                    ))}

                    {/* Route line to the nearest reachable cool point, if any */}
                    {route && route.reachable && selected && (
                        <Polyline
                            positions={[
                                [selected.current_location.lat, selected.current_location.lng],
                                [route.location.lat, route.location.lng],
                            ]}
                            pathOptions={{ color: "#38bdf8", weight: 2, dashArray: "6 6" }}
                        />
                    )}

                    {/* Workers */}
                    {workers.map((w) => (
                        <CircleMarker
                            key={w.worker_id}
                            center={[w.current_location.lat, w.current_location.lng]}
                            radius={w.worker_id === selectedWorker ? 12 : 9}
                            eventHandlers={{ click: () => handleWorkerClick(w) }}
                            pathOptions={{
                                color: RISK_HEX[w.risk_level],
                                fillColor: RISK_HEX[w.risk_level],
                                fillOpacity: 0.85,
                                weight: w.worker_id === selectedWorker ? 3 : 2,
                            }}
                        >
                            <Tooltip sticky>
                                <strong>{w.worker_id}</strong> — {w.risk_level}
                                <br />
                                {w.current_temp_c}°C · excess dose: {w.excess_dose}
                                <br />
                                <em>Click for nearest cool point</em>
                            </Tooltip>
                        </CircleMarker>
                    ))}
                </MapContainer>
            </div>

            {selectedWorker && route && (
                <div
                    style={{
                        padding: "12px 16px",
                        fontSize: "13px",
                        color: "var(--text-muted)",
                    }}
                >
                    {route.reachable ? (
                        <span>
                            <strong style={{ color: "var(--text-primary)" }}>
                                {selectedWorker}
                            </strong>{" "}
                            → {route.zone_type} ({route.temp_diff_c}°C cooler,{" "}
                            {route.distance_m}m away). Cool point temperatures are
                            modelled, not measured.
                        </span>
                    ) : (
                        <span>
                            <strong style={{ color: "var(--text-primary)" }}>
                                {selectedWorker}
                            </strong>{" "}
                            has no reachable cool point — {route.reason}
                        </span>
                    )}
                </div>
            )}
        </div>
    );
}