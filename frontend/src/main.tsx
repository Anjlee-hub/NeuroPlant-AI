import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

// Initializes i18next before first render so the shell renders translated.
import "./i18n";
import { startSyncLoop } from "@/offline/sync";
import App from "./App";
import "./styles/globals.css";

// Replays any IndexedDB-synced mutations left from a previous offline period.
startSyncLoop();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
