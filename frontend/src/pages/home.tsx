
import {
  ArrowRight,
  CalendarDays,
  Camera,
  Check,
  CloudSun,
  Languages,
  MessageCircle,
  WifiOff,
  ScanLine,
  Search,
  Sprout,
  TrendingUp,
  Volume2,
  Quote,
  type LucideIcon,
} from "lucide-react";
import { motion } from "motion/react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/stores/auth";

interface Feature {
  icon: LucideIcon;
  title: string;
  body: string;
  image?: string;
  href: string;
  visual: "image" | "language" | "calendar";
}

const features: Feature[] = [
  {
    icon: ScanLine,
    title: "feature1Title",
    body: "feature1Body",
    image:
      "https://images.unsplash.com/photo-1518531933037-91b2f5f229cc?auto=format&fit=crop&w=900&q=85",
    href: "/detect",
    visual: "image",
  },
  {
    icon: Languages,
    title: "feature2Title",
    body: "feature2Body",
    href: "/assistant",
    visual: "language",
  },
  {
    icon: WifiOff,
    title: "feature3Title",
    body: "feature3Body",
    image:
      "https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=900&q=85",
    href: "/offline",
    visual: "image",
  },
  {
    icon: CloudSun,
    title: "feature4Title",
    body: "feature4Body",
    image:
      "https://images.unsplash.com/photo-1501630834273-4b5604d2ee31?auto=format&fit=crop&w=900&q=85",
    href: "/calendar",
    visual: "image",
  },
  {
    icon: TrendingUp,
    title: "feature5Title",
    body: "feature5Body",
    image:
      "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=900&q=85",
    href: "/marketplace/browse",
    visual: "image",
  },
  {
    icon: CalendarDays,
    title: "feature6Title",
    body: "feature6Body",
    href: "/calendar",
    visual: "calendar",
  },
];

const steps = [
  { icon: Camera, title: "step1Title", body: "step1Body" },
  { icon: Search, title: "step2Title", body: "step2Body" },
  { icon: Sprout, title: "step3Title", body: "step3Body" },
];

function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.15 }}
      transition={{ duration: 0.55, delay, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}

/* Calendar illustration */
function CalendarVisual() {
  const days = [
    ["", "1", "2", "3", "4", "5", "6"],
    ["7", "8", "9", "10", "11", "12", "13"],
    ["14", "15", "16", "17", "18", "19", "20"],
    ["21", "22", "23", "24", "25", "26", "27"],
  ];

  return (
    <div className="flex h-[145px] items-center justify-center bg-gradient-to-br from-emerald-50 via-green-50 to-lime-100 p-3 dark:from-emerald-950 dark:via-green-950 dark:to-lime-950">
      <div className="w-full max-w-[230px] rounded-xl border border-white/80 bg-white p-3 shadow-lg shadow-green-900/10 dark:border-white/10 dark:bg-card">
        <div className="mb-2 flex items-center justify-between">
          <div>
            <p className="text-[9px] font-medium text-muted-foreground">
              YOUR FARM PLANNER
            </p>
            <p className="text-sm font-bold text-foreground">
              Crop calendar
            </p>
          </div>

          <div className="rounded-lg bg-emerald-100 p-2 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">
            <CalendarDays className="size-4" />
          </div>
        </div>

        <div className="mb-1 grid grid-cols-7 gap-1 text-center text-[9px] font-semibold text-muted-foreground">
          {["S", "M", "T", "W", "T", "F", "S"].map((day, i) => (
            <span key={`${day}-${i}`}>{day}</span>
          ))}
        </div>

        <div className="grid grid-cols-7 gap-1">
          {days.flat().map((day, i) => (
            <span
              key={i}
              className={`flex aspect-square items-center justify-center rounded text-[9px] ${
                day === "10"
                  ? "bg-emerald-600 font-bold text-white"
                  : day === "15" || day === "22"
                    ? "bg-amber-100 font-semibold text-amber-800 dark:bg-amber-900 dark:text-amber-200"
                    : "text-muted-foreground"
              }`}
            >
              {day}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

/* Multilingual voice illustration */
function LanguageVisual() {
  return (
    <div className="relative flex h-[145px] flex-col items-center justify-center overflow-hidden bg-gradient-to-br from-indigo-50 via-violet-50 to-fuchsia-100 p-3 dark:from-indigo-950 dark:via-violet-950 dark:to-fuchsia-950">
      <div className="absolute -right-8 -top-12 size-32 rounded-full bg-violet-300/20 blur-2xl" />
      <div className="absolute -bottom-12 -left-8 size-32 rounded-full bg-fuchsia-300/20 blur-2xl" />

      <div className="relative flex size-12 items-center justify-center rounded-xl bg-white text-violet-700 shadow-lg dark:bg-violet-900 dark:text-violet-200">
        <Volume2 className="size-6" />
      </div>

      <div className="relative mt-3 flex flex-wrap justify-center gap-1.5">
        {["हिन्दी", "ಕನ್ನಡ", "தமிழ்", "తెలుగు", "বাংলা"].map((language) => (
          <span
            key={language}
            className="rounded-full border border-white/80 bg-white/80 px-2.5 py-1 text-[10px] font-semibold text-violet-800 shadow-sm dark:border-white/10 dark:bg-white/10 dark:text-violet-100"
          >
            {language}
          </span>
        ))}
      </div>

      <p className="relative mt-2 text-[10px] font-medium text-violet-800 dark:text-violet-200">
        Your language. Your farming assistant.
      </p>
    </div>
  );
}

/* Feature visual selector */
function FeatureVisual({ feature }: { feature: Feature }) {
  if (feature.visual === "calendar") {
    return <CalendarVisual />;
  }

  if (feature.visual === "language") {
    return <LanguageVisual />;
  }

  return (
    <div className="group relative h-[145px] overflow-hidden bg-muted">
      <img
        src={feature.image}
        alt=""
        loading="lazy"
        className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
      />

      <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent" />

      <div className="absolute bottom-3 left-3 flex size-9 items-center justify-center rounded-lg border border-white/30 bg-white/20 text-white shadow-lg backdrop-blur-md">
        <feature.icon className="size-4" />
      </div>
    </div>
  );
}

export function HomePage() {
  const { t } = useTranslation();
  const user = useAuth((state) => state.user);


  return (
    <main className="overflow-hidden">
      {/* HERO SECTION */}
      <section className="relative isolate min-h-[520px] overflow-hidden bg-[#073b29] text-white">
        <img
          src="https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1800&q=90"
          alt=""
          className="absolute inset-0 -z-20 h-full w-full object-cover"
        />

        <div className="absolute inset-0 -z-10 bg-gradient-to-r from-[#042d20]/95 via-[#06452d]/85 to-[#063b29]/55" />

        <div className="pointer-events-none absolute -right-24 -top-28 size-80 rounded-full border border-white/10" />

        <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-6 py-16 sm:px-10 lg:min-h-[520px] lg:grid-cols-[1.15fr_0.85fr] lg:py-20">
          {/* Hero content */}
          <div>
            <Reveal>
              <span className="inline-flex items-center gap-2 rounded-full border border-white/30 bg-white/10 px-4 py-2 text-sm backdrop-blur">
                <Sprout className="size-4" />
                {t("landing.badge")}
              </span>
            </Reveal>

            <Reveal delay={0.1}>
              <h1 className="mt-7 max-w-2xl text-4xl font-bold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
                {t("landing.title")}
              </h1>
            </Reveal>

            <Reveal delay={0.2}>
              <p className="mt-6 max-w-xl text-base leading-8 text-emerald-50/90 sm:text-lg">
                {t("landing.subtitle")}
              </p>
            </Reveal>

            <Reveal delay={0.3}>
              <div className="mt-8 flex flex-wrap gap-3">
                <Button
                  asChild
                  size="lg"
                  className="h-12 rounded-xl bg-lime-400 px-6 font-semibold text-green-950 hover:bg-lime-300"
                >
                  <Link to="/detect">
                    <ScanLine className="mr-2 size-5" />
                    {t("landing.ctaScan")}
                    <ArrowRight className="ml-2 size-4" />
                  </Link>
                </Button>

                <Button
                  asChild
                  size="lg"
                  variant="outline"
                  className="h-12 rounded-xl border-white/40 bg-white/10 px-6 text-white backdrop-blur hover:bg-white/20 hover:text-white"
                >
                  <Link to="/assistant">
                    <MessageCircle className="mr-2 size-5" />
                    {t("landing.ctaAssistant")}
                  </Link>
                </Button>
              </div>
            </Reveal>

            <Reveal delay={0.4}>
              <div className="mt-10 flex flex-wrap gap-x-6 gap-y-3 text-sm text-emerald-50">
                <span className="flex items-center gap-2">
                  <Check className="size-4 text-lime-400" />
                  AI-assisted diagnosis
                </span>

                <span className="flex items-center gap-2">
                  <Check className="size-4 text-lime-400" />
                  Crop health insights
                </span>
              </div>
            </Reveal>
          </div>

          {/* Hero image */}
          <Reveal delay={0.2} className="relative mx-auto w-full max-w-md">
            <div className="relative rounded-[2rem] border border-white/30 bg-white/15 p-2 shadow-2xl backdrop-blur-sm">
              <img
                src="https://images.unsplash.com/photo-1518531933037-91b2f5f229cc?auto=format&fit=crop&w=900&q=90"
                alt="Close-up of healthy green leaves"
                className="h-[280px] w-full rounded-[1.5rem] object-cover sm:h-[310px]"
              />

              <div className="absolute -right-3 top-7 flex items-center gap-2 rounded-xl bg-white px-3 py-2.5 text-xs font-semibold text-green-900 shadow-lg sm:-right-5">
                <Sprout className="size-4 text-emerald-700" />
                Plant intelligence
              </div>

              <div className="absolute -bottom-4 -left-3 rounded-xl bg-white px-4 py-3 text-green-950 shadow-xl sm:-left-5">
                <div className="flex items-center gap-2">
                  <span className="flex size-8 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
                    <ScanLine className="size-4" />
                  </span>

                  <div>
                    <p className="text-xs font-bold">AI crop analysis</p>
                    <p className="text-[10px] text-gray-500">
                      Image preview ready
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* FEATURES SECTION */}
      <section className="mx-auto max-w-7xl px-6 py-16 sm:px-10">
        <Reveal>
          <div className="mx-auto max-w-2xl text-center">
            <span className="text-sm font-bold uppercase tracking-[0.18em] text-emerald-700 dark:text-emerald-400">
              NeuroPlant AI features
            </span>

            <h2 className="mt-3 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              {t("landing.featuresTitle")}
            </h2>

            <p className="mt-4 leading-7 text-muted-foreground">
              Practical digital tools to help you monitor crops, make informed
              decisions, and manage your farm.
            </p>
          </div>
        </Reveal>

        <div className="mt-10 grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {features.map((feature, index) => (
            <Reveal key={feature.title} delay={index * 0.07}>
              <Link
                to={feature.href}
                className="group block h-full rounded-2xl outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 focus-visible:ring-offset-4"
              >
                <Card className="h-full overflow-hidden rounded-2xl border border-border/70 bg-card shadow-sm transition-all duration-300 group-hover:-translate-y-1 group-hover:border-emerald-500/40 group-hover:shadow-lg">
                  <FeatureVisual feature={feature} />

                  <CardContent className="p-5">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-base font-bold tracking-tight text-foreground">
                          {t(`landing.${feature.title}`)}
                        </h3>

                        <p className="mt-2 text-sm leading-6 text-muted-foreground">
                          {t(`landing.${feature.body}`)}
                        </p>
                      </div>

                      <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-700 transition-all duration-300 group-hover:bg-emerald-600 group-hover:text-white dark:bg-emerald-950 dark:text-emerald-300">
                        <ArrowRight className="size-4 transition-transform group-hover:-rotate-45" />
                      </span>
                    </div>

                    <p className="mt-4 text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                      Explore feature
                    </p>
                  </CardContent>
                </Card>
              </Link>
            </Reveal>
          ))}
        </div>
      </section>

      {/* HOW IT WORKS */}
      
      {/* HOW IT WORKS */}
      <section className="relative overflow-hidden border-y border-emerald-100/80 bg-gradient-to-b from-emerald-50/70 via-white to-green-50/50 dark:border-emerald-900/30 dark:from-emerald-950/20 dark:via-background dark:to-green-950/20">
        {/* Decorative background */}
        <div className="pointer-events-none absolute -left-24 top-10 size-64 rounded-full bg-emerald-200/20 blur-3xl dark:bg-emerald-500/5" />
        <div className="pointer-events-none absolute -right-24 bottom-0 size-72 rounded-full bg-lime-200/20 blur-3xl dark:bg-lime-500/5" />

        <div className="relative mx-auto max-w-7xl px-6 py-20 sm:px-10">
          {/* Section heading */}
          <Reveal>
            <div className="mx-auto max-w-2xl text-center">
              <span className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white/80 px-4 py-2 text-xs font-bold uppercase tracking-[0.18em] text-emerald-700 shadow-sm dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-400">
                <Sprout className="size-4" />
                Simple workflow
              </span>

              <h2 className="mt-5 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
                {t("landing.howTitle")}
              </h2>

              <p className="mx-auto mt-4 max-w-xl text-sm leading-7 text-muted-foreground sm:text-base">
                From capturing a crop image to getting useful farming guidance,
                follow three simple steps.
              </p>
            </div>
          </Reveal>

          {/* Steps */}
          <div className="relative mt-14 grid gap-6 md:grid-cols-3">
            {/* Connecting line */}
            <div className="pointer-events-none absolute left-[16%] right-[16%] top-[39px] hidden h-px bg-gradient-to-r from-emerald-200 via-emerald-400 to-emerald-200 md:block dark:from-emerald-900 dark:via-emerald-600 dark:to-emerald-900" />

            {steps.map((step, index) => (
              <motion.div
                key={step.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{
                  duration: 0.55,
                  delay: index * 0.16,
                  ease: "easeOut",
                }}
                whileHover={{ y: -7 }}
                className="group relative"
              >
                <div className="relative h-full overflow-hidden rounded-2xl border border-emerald-100 bg-white/90 p-7 text-center shadow-[0_5px_20px_rgba(16,80,50,0.04)] transition-all duration-300 group-hover:border-emerald-300 group-hover:shadow-[0_16px_35px_rgba(16,80,50,0.10)] dark:border-emerald-900/50 dark:bg-card">
                  {/* Decorative corner */}
                  <div className="pointer-events-none absolute -right-10 -top-10 size-28 rounded-full bg-emerald-50 transition-transform duration-500 group-hover:scale-150 dark:bg-emerald-950/50" />

                  {/* Step icon */}
                  <div className="relative mx-auto flex size-16 items-center justify-center rounded-2xl border border-emerald-100 bg-gradient-to-br from-emerald-100 to-green-50 text-emerald-700 shadow-sm transition-all duration-300 group-hover:scale-110 group-hover:rotate-3 group-hover:shadow-md dark:border-emerald-800 dark:from-emerald-900 dark:to-green-950 dark:text-emerald-300">
                    <motion.div
                      animate={{ y: [0, -3, 0] }}
                      transition={{
                        duration: 2.5,
                        repeat: Infinity,
                        delay: index * 0.35,
                        ease: "easeInOut",
                      }}
                    >
                      <step.icon className="size-7" />
                    </motion.div>
                  </div>

                  {/* Step number */}
                  <div className="relative mt-5 inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.18em] text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400">
                    <span className="size-1.5 rounded-full bg-emerald-500" />
                    {t("landing.stepLabel")} 0{index + 1}
                  </div>

                  {/* Step title */}
                  <h3 className="relative mt-4 text-lg font-bold tracking-tight text-foreground transition-colors group-hover:text-emerald-700 dark:group-hover:text-emerald-400">
                    {t(`landing.${step.title}`)}
                  </h3>

                  {/* Description */}
                  <p className="relative mx-auto mt-3 max-w-sm text-sm leading-7 text-muted-foreground">
                    {t(`landing.${step.body}`)}
                  </p>

                  {/* Bottom accent */}
                  <div className="absolute bottom-0 left-1/2 h-1 w-0 -translate-x-1/2 rounded-full bg-gradient-to-r from-emerald-400 to-lime-400 transition-all duration-500 group-hover:w-2/3" />
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>


      {/* TESTIMONIALS */}
      <section className="mx-auto max-w-7xl px-6 py-16 sm:px-10">
        <Reveal>
          <div className="mx-auto max-w-2xl text-center">
            <span className="text-sm font-bold uppercase tracking-[0.18em] text-emerald-700 dark:text-emerald-400">
              Farmer experiences
            </span>

            <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
              {t("landing.testimonialsTitle")}
            </h2>
          </div>
        </Reveal>

        <div className="mt-9 grid gap-5 md:grid-cols-2">
          {["testimonial1", "testimonial2"].map((base, index) => (
            <Reveal key={base} delay={index * 0.1}>
              <Card className="h-full rounded-2xl border-border/70 shadow-sm transition-shadow hover:shadow-md">
                <CardContent className="p-6">
                  <Quote className="size-6 text-emerald-600" />

                  <p className="mt-4 text-base leading-8 text-foreground">
                    “{t(`landing.${base}Quote`)}”
                  </p>

                  <div className="mt-6 border-t border-border pt-4">
                    <p className="font-bold">
                      {t(`landing.${base}Name`)}
                    </p>

                    <p className="mt-1 text-sm text-muted-foreground">
                      {t(`landing.${base}Role`)}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </Reveal>
          ))}
        </div>
      </section>

      {/* AUTHENTICATION-AWARE CTA */}
      <section className="mx-auto max-w-7xl px-6 pb-16 sm:px-10">
        <Reveal>
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-[#0b4930] via-[#087443] to-[#159653] px-6 py-12 text-center text-white sm:px-12">
            <div className="pointer-events-none absolute -right-20 -top-32 size-80 rounded-full border border-white/10" />
            <div className="pointer-events-none absolute -bottom-40 -left-20 size-80 rounded-full border border-white/10" />

            <div className="relative mx-auto max-w-2xl">
              <div className="mx-auto flex size-12 items-center justify-center rounded-xl bg-white/15">
                <Sprout className="size-6" />
              </div>

              <h2 className="mt-5 text-3xl font-bold tracking-tight sm:text-4xl">
                {user
                  ? "Ready to check your crops?"
                  : t("landing.ctaTitle")}
              </h2>

              <p className="mt-4 leading-7 text-emerald-50/85">
                {user
                  ? "Start a new scan, review crop health, or ask your AI farming assistant for guidance."
                  : t("landing.ctaBody")}
              </p>

              <div className="mt-7 flex flex-wrap justify-center gap-3">
                <Button
                  asChild
                  size="lg"
                  className="h-11 rounded-xl bg-white px-7 font-semibold text-emerald-900 hover:bg-emerald-50"
                >
                  <Link to={user ? "/detect" : "/register"}>
                    {user ? "Start a crop scan" : t("nav.register")}
                    <ArrowRight className="ml-2 size-4" />
                  </Link>
                </Button>

                {user && (
                  <Button
                    asChild
                    size="lg"
                    variant="outline"
                    className="h-11 rounded-xl border-white/40 bg-white/10 px-7 text-white hover:bg-white/20 hover:text-white"
                  >
                    <Link to="/assistant">
                      <MessageCircle className="mr-2 size-4" />
                      Ask the assistant
                    </Link>
                  </Button>
                )}
              </div>
            </div>
          </div>
        </Reveal>
      </section>
    </main>
  );
}
