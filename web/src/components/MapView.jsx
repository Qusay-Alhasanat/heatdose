// web/src/components/MapView.jsx
import { useState, useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { getWorkers } from "../Api/client";

const RISK_COLORS = {
    low: "#4ade80",
    moderate: "#facc15",
    high: "#fb923c",
    extreme: "#ef4444",
};

// مركز تقريبي لمنطقة الدراسة بفينكس
const PHOENIX_CENTER = [33.45, -112.065];

export default function MapView() {
    const [workers, setWorkers] = useState([]);

    useEffect(() => {
        getWorkers().then(setWorkers);
    }, []);

    return (
        <MapContainer
            center={PHOENIX_CENTER}
            zoom={12}
            style={{ height: "500px", width: "100%" }}
        >
            <TileLayer
                attribution='&copy; OpenStreetMap contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {workers.map((w) => (
                <CircleMarker
                    key={w.worker_id}
                    center={[w.current_location.lat, w.current_location.lng]}
                    radius={10}
                    pathOptions={{
                        color: RISK_COLORS[w.risk_level],
                        fillColor: RISK_COLORS[w.risk_level],
                        fillOpacity: 0.8,
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
    );
}