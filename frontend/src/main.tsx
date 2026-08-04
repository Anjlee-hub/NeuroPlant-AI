import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

// Initializes i18next before first render so the shell renders translated.
import "./i18n";
import App from "./App";
import "./styles/globals.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
