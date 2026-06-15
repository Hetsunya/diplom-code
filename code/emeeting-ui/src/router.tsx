// src/router.tsx
import { createBrowserRouter } from 'react-router-dom';
import App from './App';
import { featureRoutes, publicRoutes } from "./config/features";
import { AuthGate } from "./components/AuthGate";
import AppError from "./components/AppError";

const protectedKeys = new Set([
  "sessions",
  "sessions_new",
  "analysis_configurator",
  "video_meet",
  "report",
  "report_details",
]);

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    errorElement: <AppError />,
    children: [
      ...featureRoutes
        .filter((f) => f.enabled)
        .map((f) => {
          const Component = f.component;
          const element = <Component />;
          return {
            path: f.path,
            element: protectedKeys.has(f.key) ? <AuthGate>{element}</AuthGate> : element,
          };
        }),
    ],
  },
  ...publicRoutes
    .filter((r) => r.enabled)
    .map((r) => {
      const Component = r.component;
      return { path: r.path, element: <Component /> };
    }),
]);

export default router;