// The signature element — the same four-stop thermal scale reused as
// map marker colors, risk chips, and table accents throughout the app.
export default function ThermalScale() {
    return (
        <>
            <div className="thermal-scale">
                <div className="low" />
                <div className="moderate" />
                <div className="high" />
                <div className="extreme" />
            </div>
            <div className="thermal-legend">
                <span>Low</span>
                <span>Moderate</span>
                <span>High</span>
                <span>Extreme</span>
            </div>
        </>
    );
}