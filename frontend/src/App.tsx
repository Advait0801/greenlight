import { useEffect, useRef, useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";

import { Icon } from "./components/Icon";
import { NotFound } from "./pages/NotFound";
import { loadSaved } from "./pages/YearPlan";
import { routes, NAV_GROUPS } from "./routes";

function Mark({ small }: { small?: boolean }) {
  // Three lamps, the last one lit gold: a "green light" in USC colours. Decorative.
  return (
    <span aria-hidden="true" className={`flex flex-none flex-col items-center justify-center gap-[3px] rounded-md bg-black/15 ${small ? "h-8 w-6" : "h-10 w-7"}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-white/40" />
      <span className="h-1.5 w-1.5 rounded-full bg-white/40" />
      <span className="h-1.5 w-1.5 rounded-full bg-gold" />
    </span>
  );
}

function SideNav({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav aria-label="Main" className="flex-1 overflow-y-auto px-3 py-4">
      {NAV_GROUPS.map((group) => (
        <div key={group.title} className="mb-5">
          <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-wider text-white/75">{group.title}</p>
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
                      `group flex items-center gap-3 rounded-md py-2 pr-3 text-[0.9375rem] font-medium ${
                        isActive ? "bg-white/15 text-white" : "text-white/85 hover:bg-white/10 hover:text-white"
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <span aria-hidden="true" className={`h-5 w-[3px] rounded-full ${isActive ? "bg-gold" : "bg-transparent"}`} />
                        <Icon name={route.icon ?? ""} className="h-5 w-5 flex-none" />
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
        <span className="block font-display text-xl font-semibold leading-none text-white">Greenlight</span>
        <span className="mt-1 block text-xs text-white/80">USC club planning</span>
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
  const menuButton = useRef<HTMLButtonElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const shell = useRef<HTMLDivElement>(null);
  const wasOpen = useRef(false);
  useEffect(() => {
    // The menu is modal: focus moves into it, the page behind is inert, Escape closes it, focus returns to Menu.
    const behind = shell.current;
    if (menuOpen) {
      wasOpen.current = true;
      behind?.setAttribute("inert", "");
      closeButton.current?.focus();
      const onKey = (e: globalThis.KeyboardEvent) => { if (e.key === "Escape") setMenuOpen(false); };
      window.addEventListener("keydown", onKey);
      return () => window.removeEventListener("keydown", onKey);
    }
    behind?.removeAttribute("inert");
    if (wasOpen.current) {
      wasOpen.current = false;
      menuButton.current?.focus();
    }
    return undefined;
  }, [menuOpen]);

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
          <p className="font-medium text-white">AI reads · code checks · a person approves</p>
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
              <button ref={closeButton} type="button" onClick={() => setMenuOpen(false)} className="rounded-md px-3 py-2 text-sm font-semibold ring-1 ring-white/50 hover:bg-white/10">
                Close
              </button>
            </div>
            <SideNav onNavigate={() => setMenuOpen(false)} />
          </div>
        </div>
      ) : null}

      <div ref={shell} className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-30 border-b border-stone-200 bg-white">
          <div className="flex h-16 items-center gap-3 px-4 sm:px-6 lg:px-8">
            <button
              ref={menuButton}
              type="button"
              onClick={() => setMenuOpen(true)}
              aria-expanded={menuOpen}
              className="flex items-center gap-2 rounded-lg bg-cardinal px-3 py-2 text-sm font-semibold text-white lg:hidden"
            >
              <Icon name="menu" className="h-5 w-5" /> Menu
            </button>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm text-stone-600"><span className="hidden sm:inline">{page?.group ?? "Greenlight"} <span aria-hidden="true">/</span> </span> <span className="font-medium text-stone-900">{page?.label ?? "Page not found"}</span></p>
            </div>
            <NavLink
              to="/plan"
              className="flex max-w-[11rem] items-center gap-2 rounded-md py-1 pl-1 pr-2 text-sm hover:bg-stone-100 sm:max-w-[18rem]"
            >
              <span aria-hidden="true" className="grid h-8 w-8 flex-none place-items-center rounded-full bg-cardinal font-semibold text-white">
                {(club.trim()[0] ?? "?").toUpperCase()}
              </span>
              <span className="min-w-0">
                <span className="hidden text-xs text-stone-600 sm:block">Your club</span>
                <span className="block truncate font-semibold text-stone-900">{club.trim() || "No club yet: start a year plan"}</span>
              </span>
            </NavLink>
          </div>
        </header>

        <main id="main" className="w-full max-w-[90rem] flex-1 px-4 py-8 sm:px-8 lg:px-12 lg:py-10">
          <Routes>
            {routes.map((route) => (
              <Route key={route.path} path={route.path} element={route.element} />
            ))}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
        <footer className="border-t border-stone-200 px-4 py-6 text-sm text-stone-600 sm:px-8 lg:px-12">
          Greenlight is not an official USC service. It uses public USC documents; each result shows the rule and the date of the
          version it was checked against.
        </footer>
      </div>
    </div>
  );
}
