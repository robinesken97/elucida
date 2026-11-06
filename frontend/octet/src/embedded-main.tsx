import ReactDOM from "react-dom/client";
import "@fontsource/instrument-sans/400.css";
import "@fontsource/instrument-sans/500.css";
import "@fontsource/instrument-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "../brand/tokens.css";
import Editor from "./Editor";
import "./embedded.css";
ReactDOM.createRoot(document.getElementById("root")!).render(<Editor/>);
