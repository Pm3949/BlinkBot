import ReactDOM from "react-dom/client";

import { RouterProvider } from "react-router-dom";

import { router } from "./app/routes";

import { AuthProvider } from "./context/AuthContext";

import { QueryClientProvider } from "@tanstack/react-query";

import { queryClient } from "./lib/queryClient";

import { Toaster } from "sonner";
import ErrorBoundary from "./app/ErrorBoundary";
import "./styles/theme.css";
import "./index.css";

try {
  const storedTheme = JSON.parse(
    localStorage.getItem("blinkbot-ui") || "{}",
  );

  const isDarkMode = storedTheme?.state && 'darkMode' in storedTheme.state 
    ? Boolean(storedTheme.state.darkMode) 
    : true;

  document.documentElement.classList.toggle(
    "dark",
    isDarkMode,
  );
} catch {
  document.documentElement.classList.add("dark");
}

const originalFetch = window.fetch;
window.fetch = async (...args) => {
  let [resource, config] = args;
  if (!config) config = {};
  if (!config.headers) config.headers = {};
  
  if (config.headers instanceof Headers) {
    config.headers.append('ngrok-skip-browser-warning', 'true');
  } else {
    config.headers['ngrok-skip-browser-warning'] = 'true';
  }
  
  return originalFetch(resource, config);
};


ReactDOM.createRoot(document.getElementById("root")).render(
  <QueryClientProvider client={queryClient}>
    <ErrorBoundary>
      <AuthProvider>
        <RouterProvider router={router} />
        <Toaster richColors position="top-right" />
      </AuthProvider>
    </ErrorBoundary>
  </QueryClientProvider>,
);
