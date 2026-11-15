import type { ReactElement } from "react";

import { EventPacket } from "./pages/EventPacket";
import { GapHelper } from "./pages/GapHelper";
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
}

export const routes: AppRoute[] = [
  { path: "/", element: <YearPlan />, label: "Year plan" },
  { path: "/events/packet", element: <EventPacket />, label: "Event packet" },
  { path: "/recognition", element: <Recognition />, label: "Recognition" },
  { path: "/money/check", element: <MoneyCheck />, label: "Money check" },
  { path: "/money/gap", element: <GapHelper />, label: "Funding gap" },
  { path: "/usg", element: <UsgScreen />, label: "USG screen" },
  { path: "/status", element: <Home />, label: "Status" },
];
