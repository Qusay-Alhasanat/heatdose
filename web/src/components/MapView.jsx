import { useState, useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { getWorkers } from "../Api/client";

const RISK_HEX = {
    low: "#34d399",
    moderate: "#fbbf24",
    high: "#fb923c",
    extreme: "#f87171",
};

const PHOENIX_CENTER = [33.45, -112.065];

export default function MapView() {
    const [workers, setWorkers] = useState([]);

    useEffect(() => {
        getWorkers().then(setWorkers);
    }, []);

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
                    {workers.map((w) => (
                        <CircleMarker
                            key={w.worker_id}
                            center={[w.current_location.lat, w.current_location.lng]}
                            radius={9}
                            pathOptions={{
                                color: RISK_HEX[w.risk_level],
                                fillColor: RISK_HEX[w.risk_level],
                                fillOpacity: 0.85,
                                weight: 2,
                            }}
                        >
                            <Popup>
                                <strong>{w.worker_id}</strong>
                                <br />
                                Risk: {w.risk_level}
                                <br />
                                Excess dose: {w.excess_dose}
                                <br />
                                Zone: {w.current_zone}
                            </Popup>
                        </CircleMarker>
                    ))}
                </MapContainer>
            </div>
        </div>
    );
}