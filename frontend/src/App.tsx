import { NavLink, Route, Routes } from "react-router-dom";

import { NotFound } from "./pages/NotFound";
import { routes } from "./routes";

export function App() {
  return (
    <div className="min-h-screen">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:rounded focus:bg-white focus:px-3 focus:py-2"
      >
        Skip to content
      </a>
      <header className="border-b-4 border-gold bg-cardinal text-white">
        <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <p className="text-xl font-bold tracking-tight">Greenlight</p>
          <nav aria-label="Main">
            <ul className="flex flex-wrap gap-x-4 gap-y-1">
              {routes
                .filter((route) => route.label)
                .map((route) => (
                  <li key={route.path}>
                    <NavLink
                      to={route.path}
                      end
                      className={({ isActive }) => `underline-offset-4 ${isActive ? "underline" : "hover:underline"}`}
                    >
                      {route.label}
                    </NavLink>
                  </li>
                ))}
            </ul>
          </nav>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-4xl px-4 py-8">
        <Routes>
          {routes.map((route) => (
            <Route key={route.path} path={route.path} element={route.element} />
          ))}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <footer className="mx-auto max-w-4xl px-4 pb-8 text-sm text-stone-600">
        Greenlight is not an official USC service. It uses public USC documents; each result shows the rule and the date of the
        version it was checked against.
      </footer>
    </div>
  );
}
