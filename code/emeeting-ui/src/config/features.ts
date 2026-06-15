import type React from "react";
import Dashboard from "../pages/Dashboard";
import Login from "../pages/Login";
import Sessions from "../pages/Sessions";
import NewSession from "../pages/NewSession";
import VideoMeet from "../pages/VideoMeet";
import Report from "../pages/Report";
import AnalysisConfigurator from "../pages/AnalysisConfigurator";

export type FeatureNavItem = {
  label: string;
  to: string;
};

export type FeatureRoute = {
  key: string;
  enabled: boolean;
  path: string;
  component: React.ComponentType;
  nav?: FeatureNavItem;
};

// Centralized UI routes + navigation items.
// To add a new page, enable it here and (optionally) provide `nav`.
export const featureRoutes: FeatureRoute[] = [
  {
    key: "home",
    enabled: true,
    path: "/",
    component: Dashboard,
    nav: { label: "Главная", to: "/" },
  },
  {
    key: "sessions",
    enabled: true,
    path: "/sessions",
    component: Sessions,
    nav: { label: "Сессии", to: "/sessions" },
  },
  {
    key: "sessions_new",
    enabled: true,
    path: "/sessions/new",
    component: NewSession,
  },
  {
    key: "analysis_configurator",
    enabled: true,
    path: "/analysis-configs",
    component: AnalysisConfigurator,
    nav: { label: "Конфигуратор", to: "/analysis-configs" },
  },
  {
    key: "video_meet",
    enabled: true,
    path: "/sessions/:id",
    component: VideoMeet,
  },
  {
    key: "report",
    enabled: true,
    path: "/reports",
    component: Report,
    nav: { label: "Отчеты", to: "/reports" },
  },
  {
    key: "report_details",
    enabled: true,
    path: "/reports/:id",
    component: Report,
  },
];

export const publicRoutes: Array<{
  key: string;
  enabled: boolean;
  path: string;
  component: React.ComponentType;
}> = [
  {
    key: "login",
    enabled: true,
    path: "/login",
    component: Login,
  },
];

