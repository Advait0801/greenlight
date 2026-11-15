import type { ReactElement } from "react";

import { Accuracy } from "./pages/Accuracy";
import { EventPacket } from "./pages/EventPacket";
import { GapHelper } from "./pages/GapHelper";
import { Handover } from "./pages/Handover";
import { Dashboard } from "./pages/Dashboard";
import { Home } from "./pages/Home";
import { Recognition } from "./pages/Recognition";
import { MoneyCheck } from "./pages/MoneyCheck";
import { UsgScreen } from "./pages/UsgScreen";
import { YearPlan } from "./pages/YearPlan";

// One entry per page. A feature adds its page here (and to the navigation if `label` is set).
export interface AppRoute {
  path: string;
  element: ReactElement;
  label?: string;
  group?: string;
  icon?: string;
  /** Reachable by its own link only, not listed in the sidebar. */
  hidden?: boolean;
}

export const routes: AppRoute[] = [
  { path: "/", element: <Dashboard />, label: "Home", group: "Overview", icon: "home" },
  { path: "/recognition", element: <Recognition />, label: "Recognition", group: "Your club", icon: "document" },
  { path: "/plan", element: <YearPlan />, label: "Year plan", group: "Your club", icon: "calendar" },
  { path: "/events/packet", element: <EventPacket />, label: "Events", group: "Each event", icon: "event" },
  { path: "/money/check", element: <MoneyCheck />, label: "Money check", group: "Each event", icon: "money" },
  { path: "/money/gap", element: <GapHelper />, label: "Gap helper", group: "Each event", icon: "gap" },
  { path: "/usg", element: <UsgScreen />, label: "USG screen", group: "For USG reviewers", icon: "flag" },
  { path: "/accuracy", element: <Accuracy />, label: "Accuracy", group: "Trust", icon: "accuracy" },
  { path: "/status", element: <Home />, label: "System status", group: "Trust", icon: "status", hidden: true },
  { path: "/handover", element: <Handover />, label: "Handover", group: "Your club", icon: "handover" },
];

// The sidebar's sections, in the order a club works through them.
export const NAV_GROUPS: { title: string; paths: string[] }[] = [
  { title: "Overview", paths: ["/"] },
  { title: "Your club", paths: ["/recognition", "/plan", "/handover"] },
  { title: "Each event", paths: ["/events/packet", "/money/check", "/money/gap"] },
  { title: "For USG reviewers", paths: ["/usg"] },
  { title: "Trust", paths: ["/accuracy"] },
];
