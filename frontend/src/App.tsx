import { useEffect, useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";

import { NotFound } from "./pages/NotFound";
import { loadSaved } from "./pages/YearPlan";
import { routes, NAV_GROUPS } from "./routes";

function Mark({ small }: { small?: boolean }) {
  // Three lamps, the last one lit gold: a "green light" in USC colours. Decorative.
  return (
    <span aria-hidden="true" className={`flex flex-none flex-col items-center justify-center gap-[3px] rounded-xl bg-white/10 ring-1 ring-white/25 ${small ? "h-8 w-8" : "h-10 w-10"}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-white/35" />
      <span className="h-1.5 w-1.5 rounded-full bg-white/35" />
      <span className="h-2 w-2 rounded-full bg-gold shadow-[0_0_8px_2px_rgba(255,204,0,0.7)]" />
    </span>
  );
}

function SideNav({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav aria-label="Main" className="flex-1 overflow-y-auto px-3 py-4">
      {NAV_GROUPS.map((group) => (
        <div key={group.title} className="mb-5">
          <p className="px-3 pb-1.5 text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-white/70">{group.title}</p>
          <ul className="space-y-0.5">
            {group.paths.map((path) => {
              const route = routes.find((r) => r.path === path);
              if (!route?.label) return null;
              return (
                <li key={path}>
                  <NavLink
                    to={path}
                    end
                    onClick={onNavigate}
                    className={({ isActive }) =>
                      `group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                        isActive ? "bg-white text-cardinal shadow-sm" : "text-white/90 hover:bg-white/10 hover:text-white"
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <span aria-hidden="true" className={`h-5 w-1 rounded-full ${isActive ? "bg-gold" : "bg-transparent group-hover:bg-white/30"}`} />
                        <span aria-hidden="true" className="w-5 text-center text-base leading-none">{route.icon}</span>
                        {route.label}
                      </>
                    )}
                  </NavLink>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

function Brand() {
  return (
    <NavLink to="/" className="flex items-center gap-3 rounded-lg px-2 py-1">
      <Mark />
      <span>
        <span className="block font-display text-xl font-semibold leading-none tracking-tight text-white">Greenlight</span>
        <span className="mt-1 block text-xs text-white/80">USC club planning portal</span>
      </span>
    </NavLink>
  );
}

export function App() {
  const { pathname } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [club, setClub] = useState(() => loadSaved().club_name);
  useEffect(() => {
    window.scrollTo(0, 0);
    setMenuOpen(false);
    setClub(loadSaved().club_name);
  }, [pathname]);
  useEffect(() => {
    // The year plan saves the club as it is edited; pick up its name without a reload.
    const timer = window.setInterval(() => setClub(loadSaved().club_name), 1500);
    return () => window.clearInterval(timer);
  }, []);
  const page = routes.find((r) => r.path === pathname);

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[17rem_1fr] lg:bg-[linear-gradient(to_right,#990000_17rem,transparent_17rem)]">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2"
      >
        Skip to content
      </a>

      {/* Sidebar (large screens) */}
      <aside className="hidden bg-cardinal text-white lg:sticky lg:top-0 lg:flex lg:h-screen lg:flex-col">
        <div className="border-b border-white/15 px-4 py-5"><Brand /></div>
        <SideNav />
        <div className="border-t border-white/15 px-5 py-4 text-xs text-white/80">
          <p className="font-semibold text-gold">AI reads · code checks · a person approves</p>
          <p className="mt-1">Not an official USC service.</p>
        </div>
      </aside>

      {/* Phone and tablet: a menu drawer */}
      {menuOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <button type="button" aria-label="Close the menu" className="absolute inset-0 bg-stone-950/50" onClick={() => setMenuOpen(false)} />
          <div className="relative flex h-full w-72 max-w-[85vw] flex-col bg-cardinal text-white shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/15 px-4 py-4">
              <Brand />
              <button type="button" onClick={() => setMenuOpen(false)} className="rounded-lg px-3 py-2 text-sm font-semibold ring-1 ring-white/40 hover:bg-white/10">
                Close
              </button>
            </div>
            <SideNav onNavigate={() => setMenuOpen(false)} />
          </div>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-30 border-b border-stone-200 bg-white/95 backdrop-blur">
          <div className="flex h-16 items-center gap-3 px-4 sm:px-6 lg:px-8">
            <button
              type="button"
              onClick={() => setMenuOpen(true)}
              aria-expanded={menuOpen}
              className="flex items-center gap-2 rounded-lg bg-cardinal px-3 py-2 text-sm font-semibold text-white lg:hidden"
            >
              <span aria-hidden="true">☰</span> Menu
            </button>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold uppercase tracking-[0.14em] text-cardinal">{page?.group ?? "Greenlight"}</p>
              <p className="truncate font-display text-lg font-semibold leading-tight text-stone-950">{page?.label ?? "Page not found"}</p>
            </div>
            <NavLink
              to="/plan"
              className="hidden max-w-[16rem] items-center gap-2 rounded-full border border-stone-200 bg-stone-50 py-1 pl-1 pr-3 text-sm hover:border-cardinal sm:flex"
            >
              <span aria-hidden="true" className="grid h-7 w-7 flex-none place-items-center rounded-full bg-gold font-bold text-stone-950">
                {(club.trim()[0] ?? "?").toUpperCase()}
              </span>
              <span className="min-w-0">
                <span className="block text-[0.65rem] font-semibold uppercase tracking-wide text-stone-600">Your club</span>
                <span className="block truncate font-semibold text-stone-900">{club.trim() || "No club yet: start a year plan"}</span>
              </span>
            </NavLink>
          </div>
          <div aria-hidden="true" className="h-1 bg-gradient-to-r from-cardinal via-cardinal to-gold" />
        </header>

        <main id="main" className="flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Routes>
            {routes.map((route) => (
              <Route key={route.path} path={route.path} element={route.element} />
            ))}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
        <footer className="border-t border-stone-200 bg-white px-4 py-5 text-sm text-stone-600 sm:px-6 lg:px-8">
          Greenlight is not an official USC service. It uses public USC documents; each result shows the rule and the date of the
          version it was checked against.
        </footer>
      </div>
    </div>
  );
}
