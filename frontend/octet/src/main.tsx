import React from "react";
import ReactDOM from "react-dom/client";
// Brand fonts are bundled so the app works offline (OFL-1.1).
import "@fontsource/instrument-sans/400.css";
import "@fontsource/instrument-sans/500.css";
import "@fontsource/instrument-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "../brand/tokens.css"; // before App, which reads drawing tokens at load
import App from "./App";
import { watchErrors } from "./crashlog";

watchErrors();
// In development the app measures its own controls and says so in the console when they do not match (lookwatch.ts).
if (import.meta.env.DEV) void import("./lookwatch").then((m) => m.watchLook());

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
