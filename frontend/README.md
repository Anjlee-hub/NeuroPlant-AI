# NeuroPlant AI — Frontend

React + Vite + TypeScript + Tailwind CSS + shadcn/ui (PWA, offline-first).

## Local dev

```bash
npm install --include=dev   # see NODE_ENV note below
npm run dev      # → http://localhost:5173  (proxies /api → localhost:8000)
npm run build    # type-check (tsc -b) + production build to dist/ (PWA)
npm run typecheck
npm test         # Vitest + Testing Library (jsdom)
npm run lint     # ESLint (flat config, --max-warnings=0)
```

> **NODE_ENV note:** the dev shell exports `NODE_ENV=production`, which makes
> plain `npm install` skip devDependencies. Use `npm install --include=dev`
> (or `NODE_ENV= npm install`). The Vitest config forces `NODE_ENV=test` so
> React resolves its development build regardless.

## Tests

Component/unit tests live next to the code in `__tests__/` (see
`vitest.config.ts` and `src/test/setup.ts`). Current coverage:
`LanguageSwitcher`, `ThemeToggle`, and `LoginPage` (password/OTP/MFA flows).

## Structure (grows per milestone)

```
src/
├── app/          # providers, router, error boundaries          (M1)
├── components/   # shared cards, charts, voice bar, heatmap
├── features/     # auth·detection·cropDoctor·assistant·voice·weather·
│                 # outbreaks·soil·calendar·yield·prices·finance·marketplace·
│                 # store·community·experts·analytics·admin·notifications
├── offline/      # service worker, IndexedDB store, sync queue   (M1/M2)
├── hooks/  lib/  stores/  pages/  types/
└── locales/      # 12-language JSON packs                        (M4)
```
