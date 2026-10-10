import { createBrowserRouter } from "react-router";

import { AppShell } from "./components/AppShell";
import { AlertsPage } from "./pages/AlertsPage";
import { ComparePage } from "./pages/ComparePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ProfilesPage } from "./pages/ProfilesPage";
import { ProfileWizardPage } from "./pages/ProfileWizardPage";
import { PropertyPage } from "./pages/PropertyPage";
import { RunPage } from "./pages/RunPage";
import { SavedPage } from "./pages/SavedPage";
import { PortfolioPage } from "./pages/PortfolioPage";

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: "/", element: <ProfilesPage /> },
      { path: "/profiles/new", element: <ProfileWizardPage /> },
      { path: "/profiles/:profileId/edit", element: <ProfileWizardPage /> },
      { path: "/runs/:runId", element: <RunPage /> },
      { path: "/runs/:runId/properties/:listingId", element: <PropertyPage /> },
      { path: "/properties/:listingId", element: <PropertyPage /> },
      { path: "/saved", element: <SavedPage /> },
      { path: "/portfolio", element: <PortfolioPage /> },
      { path: "/compare", element: <ComparePage /> },
      { path: "/alerts", element: <AlertsPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
