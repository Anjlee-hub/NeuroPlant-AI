import { motion } from "motion/react";

/**
 * M0 placeholder shell.
 * Milestone 1 replaces this with the real app shell (router, providers,
 * shadcn/ui design system, i18n, PWA offline layer).
 */
export default function App() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-stone-950 text-stone-100">
      <div className="mx-auto max-w-xl px-6 text-center">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <p className="text-sm font-medium uppercase tracking-widest text-green-500">
            NeuroPlant AI
          </p>
          <h1 className="mt-3 text-3xl font-bold">
            The AI-powered Agriculture Platform
          </h1>
          <p className="mt-3 text-stone-400">
            Milestone 0 scaffold — disease detection, treatments, weather,
            marketplace and more arrive milestone by milestone.
          </p>
        </motion.div>
      </div>
    </main>
  );
}
