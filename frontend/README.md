# Frontend

React, Vite, TypeScript (strict) and Tailwind CSS. Node 20.19 or later.

```bash
npm install
npm run dev      # http://localhost:${FRONTEND_PORT:-5173}
npm run build    # type-check, then build to dist/
```

| Variable | Default | Meaning |
|---|---|---|
| `FRONTEND_PORT` | `5173` | dev and preview server port (fails if taken) |
| `BACKEND_PORT` | `8000` | used for the default proxy target |
| `API_PROXY_TARGET` | `http://localhost:$BACKEND_PORT` | where `/api` is forwarded in development |
| `VITE_API_BASE_URL` | `/api` | base URL the browser uses for API calls |

Variables are read from the shell or from the repository's `.env` (`envDir` is the repository root). Only `VITE_` variables reach the browser.

```
src/
  routes.tsx    one entry per page; add a feature's page here
  pages/        Home (status for now; the year plan becomes the home screen in Phase 4), NotFound
  components/   StatusBadge (icon + text, never colour alone), SourceLink (rule text + source), PrecheckNotice
  api/          typed client for the backend (client.ts, types.ts)
```

Design rules:
- The home screen is a calendar and a budget, not a chat window.
- Red, yellow and green always come with an icon and a text label.
- Everything works with the keyboard and on a phone.
- Plain language. No office acronym without its full name.
- Every finding shows its rule text and a link to the source.
