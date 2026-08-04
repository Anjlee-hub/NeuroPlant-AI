import {
  ArrowRight,
  Camera,
  MessageCircle,
  Quote,
  ScanLine,
  Search,
  Sprout,
  Stethoscope,
  WifiOff,
  type LucideIcon,
} from "lucide-react";
import { motion } from "motion/react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface Feature {
  icon: LucideIcon;
  title: string;
  body: string;
}

interface Step {
  icon: LucideIcon;
  title: string;
  body: string;
}

/** Scroll-reveal wrapper — fades content in once as it enters the viewport. */
function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.5, delay }}
    >
      {children}
    </motion.div>
  );
}

export function HomePage() {
  const { t } = useTranslation();

  const features: Feature[] = [
    { icon: ScanLine, title: t("landing.feature1Title"), body: t("landing.feature1Body") },
    { icon: MessageCircle, title: t("landing.feature2Title"), body: t("landing.feature2Body") },
    { icon: WifiOff, title: t("landing.feature3Title"), body: t("landing.feature3Body") },
    { icon: Stethoscope, title: t("landing.feature4Title"), body: t("landing.feature4Body") },
    { icon: ArrowRight, title: t("landing.feature5Title"), body: t("landing.feature5Body") },
    { icon: Sprout, title: t("landing.feature6Title"), body: t("landing.feature6Body") },
  ];

  const steps: Step[] = [
    { icon: Camera, title: t("landing.step1Title"), body: t("landing.step1Body") },
    { icon: Search, title: t("landing.step2Title"), body: t("landing.step2Body") },
    { icon: Sprout, title: t("landing.step3Title"), body: t("landing.step3Body") },
  ];

  return (
    <>
      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        <div
          aria-hidden
          className="absolute inset-0 -z-10 bg-gradient-to-b from-brand-50 via-background to-background dark:from-brand-950/50"
        />
        <div className="mx-auto flex max-w-6xl flex-col items-center px-6 py-20 text-center sm:py-28">
          <Reveal>
            <p className="inline-flex items-center rounded-full border border-brand-300 bg-brand-50 px-3 py-1 text-sm font-medium text-brand-800 dark:border-brand-800 dark:bg-brand-950 dark:text-brand-200">
              {t("landing.badge")}
            </p>
          </Reveal>
          <Reveal delay={0.1}>
            <h1 className="mt-6 max-w-3xl text-4xl font-bold tracking-tight sm:text-6xl">
              {t("landing.title")}
            </h1>
          </Reveal>
          <Reveal delay={0.2}>
            <p className="mt-6 max-w-2xl text-lg text-muted-foreground">
              {t("landing.subtitle")}
            </p>
          </Reveal>
          <Reveal delay={0.3}>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <Button asChild size="lg">
                <Link to="/detect">
                  <ScanLine />
                  {t("landing.ctaScan")}
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link to="/register">
                  <MessageCircle />
                  {t("landing.ctaAssistant")}
                </Link>
              </Button>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── Features ─────────────────────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <Reveal>
          <h2 className="text-center text-3xl font-bold tracking-tight">
            {t("landing.featuresTitle")}
          </h2>
        </Reveal>
        <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((feature, index) => (
            <Reveal key={feature.title} delay={index * 0.05}>
              <Card className="h-full">
                <CardHeader>
                  <span className="mb-2 flex size-11 items-center justify-center rounded-lg bg-brand-100 text-brand-700 dark:bg-brand-900/50 dark:text-brand-300">
                    <feature.icon className="size-5" />
                  </span>
                  <CardTitle className="text-lg">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-base">
                    {feature.body}
                  </CardDescription>
                </CardContent>
              </Card>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────────── */}
      <section className="border-y border-border bg-muted/40">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <Reveal>
            <h2 className="text-center text-3xl font-bold tracking-tight">
              {t("landing.howTitle")}
            </h2>
          </Reveal>
          <ol className="mt-10 grid gap-8 md:grid-cols-3">
            {steps.map((step, index) => (
              <Reveal key={step.title} delay={index * 0.1}>
                <li className="flex flex-col items-center gap-3 text-center">
                  <span className="flex size-12 items-center justify-center rounded-full bg-primary text-primary-foreground">
                    <step.icon className="size-5" />
                  </span>
                  <span className="text-sm font-medium uppercase tracking-widest text-brand-600 dark:text-brand-400">
                    {t("landing.stepLabel")} {index + 1}
                  </span>
                  <h3 className="text-xl font-semibold">{step.title}</h3>
                  <p className="text-muted-foreground">{step.body}</p>
                </li>
              </Reveal>
            ))}
          </ol>
        </div>
      </section>

      {/* ── Testimonials ─────────────────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <Reveal>
          <h2 className="text-center text-3xl font-bold tracking-tight">
            {t("landing.testimonialsTitle")}
          </h2>
        </Reveal>
        <div className="mt-10 grid gap-6 md:grid-cols-2">
          {["testimonial1", "testimonial2"].map((base, index) => (
            <Reveal key={base} delay={index * 0.1}>
              <Card className="h-full">
                <CardContent className="flex flex-col gap-4 p-6">
                  <Quote className="size-6 text-brand-500" />
                  <p className="text-lg text-foreground">{t(`landing.${base}Quote`)}</p>
                  <div>
                    <p className="font-semibold">{t(`landing.${base}Name`)}</p>
                    <p className="text-sm text-muted-foreground">
                      {t(`landing.${base}Role`)}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-6 pb-20">
        <Reveal>
          <div className="flex flex-col items-center gap-4 rounded-2xl bg-primary px-6 py-14 text-center text-primary-foreground">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              {t("landing.ctaTitle")}
            </h2>
            <p className="max-w-xl text-primary-foreground/85">{t("landing.ctaBody")}</p>
            <Button
              asChild
              size="lg"
              variant="secondary"
              className="mt-2 bg-background text-foreground hover:bg-background/90"
            >
              <Link to="/register">
                {t("nav.register")}
                <ArrowRight />
              </Link>
            </Button>
          </div>
        </Reveal>
      </section>
    </>
  );
}
