# PRISM Frontend

Next.js web app for PRISM FinOps. Talks to [`prism-backend`](../prism-backend) over REST (`/v1/...`) and WebSocket (`/ws`).

## Stack

- Next.js (App Router) · React · TypeScript  
- TanStack Query · Zustand · Axios  
- Tailwind CSS · Vitest  

## Quick start

From repo root, prefer the full flow in [`../Guide.md`](../Guide.md). Short version:

```powershell
cd prism-frontend
npm install --legacy-peer-deps
```

Create `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_WS_URL=ws://127.0.0.1:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_LLM_STREAMING=false
```

Run (backend must already be up):

```powershell
npm run dev
```

Open http://localhost:3000 (or use `npx next dev -p 3001` if 3000 is busy).

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Dev server |
| `npm run build` | Production build |
| `npm run start` | Serve production build |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run test` | Vitest |
| `npm run lint` | ESLint |

## Notes

- API response adapters live under `src/lib/api/` (normalize backend `{ data, pagination }` / bare arrays / field renames).  
- Auth: access token in memory; refresh in `sessionStorage`; WS auth uses `Sec-WebSocket-Protocol` (not query-string JWT).  
- Request correlation: client sends `X-Request-Id`; backend echoes it on responses.
