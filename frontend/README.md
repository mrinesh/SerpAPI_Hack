# Frontend

React 19 + TypeScript (Vite), Tailwind CSS, React Router, TanStack Query, Leaflet.

```bash
npm install
npm run dev        # http://localhost:5173, proxies /api to http://localhost:8000
npm run typecheck
npm run lint
npm run gen:types  # regenerate src/api/schema.d.ts from ../backend/openapi.json
```

| Path | What |
|---|---|
| `src/api/client.ts` | The only HTTP client; turns backend errors into `ApiError` |
| `src/api/schema.d.ts` | Generated from the backend's OpenAPI schema. Do not edit |
| `src/api/types.ts` | Friendly aliases for the generated types |
| `src/api/hooks.ts` | TanStack Query hooks, one per endpoint |
| `src/pages/` | One component per route (see `src/router.tsx`) |
| `src/components/` | Shared UI |

Full docs: [../docs/README.md](../docs/README.md).
