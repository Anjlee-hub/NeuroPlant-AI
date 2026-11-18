
import React, { useState } from "react";
import PlantRegistration from "./PlantRegistration";
import PlantMonitoring from "./PlantMonitoring";
import "./App.css";

const App: React.FC = () => {
  const [page, setPage] = useState<"register" | "monitor">("register");

  return (
    <div>
      <nav className="navbar">
        <h2>🌱 NeuroPlant AI</h2>

        <div>
          <button onClick={() => setPage("register")}>
            Plant Registration
          </button>

          <button onClick={() => setPage("monitor")}>
            Plant Monitoring
          </button>
        </div>
      </nav>

      {page === "register" ? (
        <PlantRegistration />
      ) : (
        <PlantMonitoring />
      )}
    </div>
  );
};

export default App;
