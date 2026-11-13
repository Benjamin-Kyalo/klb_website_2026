import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import { OptionsProvider } from "./context/OptionsContext.jsx";
import { SiteProvider } from "./context/SiteContext.jsx";
import { applyA11yPrefs, loadA11yPrefs } from "./lib/accessibility.js";
import "./styles/klb.css";
import "./styles/react.css";
import "./styles/admin.css";
import "./styles/admin-react.css";
import "./styles/accessibility.css";

// Apply saved accessibility preferences before the first render so the page
// does not flash at the default size or colour scheme.
applyA11yPrefs(loadA11yPrefs());

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <SiteProvider>
          <AuthProvider>
            <OptionsProvider>
              <App />
            </OptionsProvider>
          </AuthProvider>
        </SiteProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>
);
