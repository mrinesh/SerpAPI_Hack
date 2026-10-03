import { createBrowserRouter } from "react-router";

import { AppShell } from "./components/AppShell";
import { AlertsPage } from "./pages/AlertsPage";
import { ComparePage } from "./pages/ComparePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { PropertyPage } from "./pages/PropertyPage";
import { RunPage } from "./pages/RunPage";
import { SavedPage } from "./pages/SavedPage";

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: "/", element: <OnboardingPage /> },
      { path: "/runs/:runId", element: <RunPage /> },
      { path: "/properties/:listingId", element: <PropertyPage /> },
      { path: "/saved", element: <SavedPage /> },
      { path: "/compare", element: <ComparePage /> },
      { path: "/alerts", element: <AlertsPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
