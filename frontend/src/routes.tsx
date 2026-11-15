import type { ReactElement } from "react";

import { EventPacket } from "./pages/EventPacket";
import { Home } from "./pages/Home";

// One entry per page. A feature adds its page here (and to the navigation if `label` is set).
export interface AppRoute {
  path: string;
  element: ReactElement;
  label?: string;
}

export const routes: AppRoute[] = [
  { path: "/", element: <Home />, label: "Start" },
  { path: "/events/packet", element: <EventPacket />, label: "Event packet" },
];
