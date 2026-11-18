
import {
  Users,
  Sprout,
  ScanLine,
  Store,
  Activity,
  ShieldCheck,
  TrendingUp,
  UserCheck,
} from "lucide-react";

const stats = [
  {
    title: "Total Users",
    value: "—",
    description: "Registered platform users",
    icon: Users,
  },
  {
    title: "Farmers",
    value: "—",
    description: "Registered farmers",
    icon: Sprout,
  },
  {
    title: "Plant Scans",
    value: "—",
    description: "Total AI plant scans",
    icon: ScanLine,
  },
  {
    title: "Sellers",
    value: "—",
    description: "Marketplace sellers",
    icon: Store,
  },
];

export default function AdminDashboard() {
  return (
    <div className="min-h-screen bg-background p-6 md:p-8">
      <div className="mx-auto max-w-7xl space-y-8">

        {/* Header */}
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <ShieldCheck className="h-4 w-4" />
            Administrator
          </div>

          <h1 className="mt-2 text-3xl font-bold tracking-tight">
            Admin Dashboard
          </h1>

          <p className="mt-2 text-muted-foreground">
            Monitor and manage your NeuroPlant-AI platform.
          </p>
        </div>

        {/* Backend connection notice */}
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          Dashboard layout is ready. Live statistics will appear after
          connecting the admin backend APIs.
        </div>

        {/* Statistics */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((item) => {
            const Icon = item.icon;

            return (
              <div
                key={item.title}
                className="rounded-xl border bg-card p-5 shadow-sm"
              >
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-muted-foreground">
                    {item.title}
                  </p>
                  <Icon className="h-5 w-5 text-primary" />
                </div>

                <h2 className="mt-4 text-3xl font-bold">
                  {item.value}
                </h2>

                <p className="mt-2 text-xs text-muted-foreground">
                  {item.description}
                </p>
              </div>
            );
          })}
        </div>

        {/* Platform overview */}
        <div className="grid gap-6 lg:grid-cols-2">

          <div className="rounded-xl border bg-card p-6">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              <h2 className="text-lg font-semibold">
                Platform Overview
              </h2>
            </div>

            <p className="mt-2 text-sm text-muted-foreground">
              Your platform monitoring overview.
            </p>

            <div className="mt-6 space-y-4">
              {[
                "User registrations",
                "Plant monitoring",
                "AI disease detection",
                "Marketplace activity",
              ].map((item) => (
                <div
                  key={item}
                  className="flex items-center justify-between border-b pb-3 last:border-0"
                >
                  <span className="text-sm">{item}</span>
                  <span className="text-xs text-muted-foreground">
                    Awaiting data
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border bg-card p-6">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary" />
              <h2 className="text-lg font-semibold">
                System Status
              </h2>
            </div>

            <p className="mt-2 text-sm text-muted-foreground">
              Platform administration and monitoring.
            </p>

            <div className="mt-6 space-y-5">
              <div className="flex items-center gap-3">
                <UserCheck className="h-5 w-5 text-primary" />
                <div>
                  <p className="text-sm font-medium">User Management</p>
                  <p className="text-xs text-muted-foreground">
                    Admin API connection pending
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <ScanLine className="h-5 w-5 text-primary" />
                <div>
                  <p className="text-sm font-medium">AI Scan Monitoring</p>
                  <p className="text-xs text-muted-foreground">
                    Admin API connection pending
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <ShieldCheck className="h-5 w-5 text-primary" />
                <div>
                  <p className="text-sm font-medium">Access Security</p>
                  <p className="text-xs text-muted-foreground">
                    Admin authorization setup pending
                  </p>
                </div>
              </div>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
