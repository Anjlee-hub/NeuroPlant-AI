
import { useMemo, useState } from "react";
import {
  Users,
  Search,
  ShieldCheck,
  UserRound,
  Filter,
} from "lucide-react";

type UserRole = "farmer" | "customer" | "expert" | "seller";

interface PlatformUser {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  status: "Active" | "Inactive";
}

const initialUsers: PlatformUser[] = [];

export default function PlatformManagement() {
  const [users, setUsers] = useState<PlatformUser[]>(initialUsers);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");

  const filteredUsers = useMemo(() => {
    return users.filter((user) => {
      const matchesSearch =
        user.name.toLowerCase().includes(search.toLowerCase()) ||
        user.email.toLowerCase().includes(search.toLowerCase());

      const matchesRole =
        roleFilter === "all" || user.role === roleFilter;

      return matchesSearch && matchesRole;
    });
  }, [users, search, roleFilter]);

  function toggleStatus(id: number) {
    setUsers((current) =>
      current.map((user) =>
        user.id === id
          ? {
              ...user,
              status:
                user.status === "Active" ? "Inactive" : "Active",
            }
          : user
      )
    );
  }

  return (
    <div className="min-h-screen bg-background p-6 md:p-8">
      <div className="mx-auto max-w-7xl space-y-8">

        {/* Header */}
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <ShieldCheck className="h-4 w-4" />
            Administration
          </div>

          <h1 className="mt-2 text-3xl font-bold tracking-tight">
            Platform Management
          </h1>

          <p className="mt-2 text-muted-foreground">
            Manage users and monitor platform accounts.
          </p>
        </div>

        {/* Notice */}
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          User management interface is ready. Connect the protected
          backend admin APIs before managing real accounts.
        </div>

        {/* User summary */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">

          <div className="rounded-xl border bg-card p-5">
            <Users className="h-6 w-6 text-primary" />
            <p className="mt-3 text-sm text-muted-foreground">
              Total Users
            </p>
            <h2 className="mt-1 text-3xl font-bold">
              {users.length}
            </h2>
          </div>

          <div className="rounded-xl border bg-card p-5">
            <UserRound className="h-6 w-6 text-primary" />
            <p className="mt-3 text-sm text-muted-foreground">
              Active Users
            </p>
            <h2 className="mt-1 text-3xl font-bold">
              {users.filter((u) => u.status === "Active").length}
            </h2>
          </div>

          <div className="rounded-xl border bg-card p-5">
            <ShieldCheck className="h-6 w-6 text-primary" />
            <p className="mt-3 text-sm text-muted-foreground">
              Inactive Users
            </p>
            <h2 className="mt-1 text-3xl font-bold">
              {users.filter((u) => u.status === "Inactive").length}
            </h2>
          </div>

        </div>

        {/* Search and filters */}
        <div className="rounded-xl border bg-card p-5">

          <div className="flex items-center gap-2">
            <Filter className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">
              User Management
            </h2>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2">

            <div className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />

              <input
                type="text"
                placeholder="Search by name or email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-md border bg-background py-2.5 pl-10 pr-3 text-sm outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="rounded-md border bg-background px-3 py-2.5 text-sm"
            >
              <option value="all">All Roles</option>
              <option value="farmer">Farmer</option>
              <option value="customer">Customer</option>
              <option value="expert">Expert</option>
              <option value="seller">Seller</option>
            </select>

          </div>

          {/* User table */}
          <div className="mt-6 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b text-muted-foreground">
                  <th className="px-3 py-3 font-medium">User</th>
                  <th className="px-3 py-3 font-medium">Role</th>
                  <th className="px-3 py-3 font-medium">Status</th>
                  <th className="px-3 py-3 font-medium">Action</th>
                </tr>
              </thead>

              <tbody>
                {filteredUsers.length > 0 ? (
                  filteredUsers.map((user) => (
                    <tr key={user.id} className="border-b last:border-0">
                      <td className="px-3 py-4">
                        <p className="font-medium">{user.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {user.email}
                        </p>
                      </td>

                      <td className="px-3 py-4 capitalize">
                        {user.role}
                      </td>

                      <td className="px-3 py-4">
                        <span
                          className={`rounded-full px-3 py-1 text-xs ${
                            user.status === "Active"
                              ? "bg-green-100 text-green-700"
                              : "bg-red-100 text-red-700"
                          }`}
                        >
                          {user.status}
                        </span>
                      </td>

                      <td className="px-3 py-4">
                        <button
                          type="button"
                          onClick={() => toggleStatus(user.id)}
                          className="rounded-md border px-3 py-1.5 text-xs hover:bg-muted"
                        >
                          Toggle Status
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td
                      colSpan={4}
                      className="px-3 py-12 text-center text-muted-foreground"
                    >
                      <Users className="mx-auto mb-3 h-8 w-8 opacity-50" />
                      <p className="font-medium">No users available</p>
                      <p className="mt-1 text-xs">
                        Connect the admin users API to load real platform accounts.
                      </p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

        </div>

      </div>
    </div>
  );
}
