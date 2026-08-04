# NeuroPlant AI — Frontend

React + Vite + TypeScript + Tailwind CSS + shadcn/ui (PWA, offline-first).

## Local dev

```bash
npm install
npm run dev      # → http://localhost:5173  (proxies /api → localhost:8000)
npm run build    # type-check (tsc -b) + production build to dist/
npm run typecheck
```

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
