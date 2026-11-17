
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Leaf, FileText, Loader2 } from "lucide-react";

export default function PlantHealthReport() {
  const [scanId, setScanId] = useState("");

  const scansQuery = useQuery({
    queryKey: ["plant-health-reports"],
    queryFn: () => api.listScans(),
  });

  const scans = scansQuery.data?.items ?? [];

  const filteredScans = scans.filter((scan) =>
    scanId.trim()
      ? String(scan.id) === scanId.trim()
      : true
  );

  function getHealthStatus(severity: string | null) {
    if (!severity) return "Status unavailable";
    if (severity.toLowerCase().includes("severe")) return "Needs urgent attention";
    if (severity.toLowerCase().includes("moderate")) return "Needs treatment";
    if (severity.toLowerCase().includes("mild")) return "Mild symptoms";
    return "Check recommended";
  }

  return (
    <main className="min-h-screen bg-green-50 px-4 py-8">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 flex items-center gap-3">
          <div className="rounded-xl bg-green-700 p-3 text-white">
            <FileText size={28} />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-green-900">
              Plant Health Reports
            </h1>
            <p className="text-gray-600">
              View AI scan results and monitor plant health.
            </p>
          </div>
        </div>

        <div className="mb-6 rounded-xl bg-white p-5 shadow-sm">
          <label className="mb-2 block font-semibold text-gray-800">
            Search by Scan ID
          </label>
          <input
            type="number"
            min="1"
            value={scanId}
            onChange={(event) => setScanId(event.target.value)}
            placeholder="Enter scan ID or leave empty to view all"
            className="w-full rounded-lg border p-3"
          />
        </div>

        {scansQuery.isLoading && (
          <p className="flex items-center gap-2 text-green-800">
            <Loader2 className="animate-spin" /> Loading health reports...
          </p>
        )}

        {scansQuery.isError && (
          <p className="rounded-lg bg-red-100 p-4 text-red-700">
            Could not load reports. Please check your backend connection.
          </p>
        )}

        {!scansQuery.isLoading && !scansQuery.isError && (
          <div className="space-y-4">
            <div className="rounded-xl bg-white p-5 shadow-sm">
              <p className="text-sm text-gray-500">Total AI scans</p>
              <p className="text-3xl font-bold text-green-800">
                {scans.length}
              </p>
            </div>

            {filteredScans.length === 0 ? (
              <div className="rounded-xl bg-white p-8 text-center text-gray-600">
                No scan reports found.
              </div>
            ) : (
              filteredScans.map((scan) => (
                <article
                  key={scan.id}
                  className="rounded-xl bg-white p-6 shadow-sm"
                >
                  <div className="mb-4 flex items-center gap-3">
                    <Leaf className="text-green-700" />
                    <h2 className="text-xl font-bold text-green-900">
                      Plant Health Report #{scan.id}
                    </h2>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <p className="text-sm text-gray-500">Detected disease</p>
                      <p className="font-semibold">{scan.disease_name || "Not identified"}</p>
                    </div>

                    <div>
                      <p className="text-sm text-gray-500">Confidence</p>
                      <p className="font-semibold">
                        {(scan.confidence * 100).toFixed(2)}%
                      </p>
                    </div>

                    <div>
                      <p className="text-sm text-gray-500">Severity</p>
                      <p className="font-semibold">{scan.severity ?? "Unavailable"}</p>
                    </div>

                    <div>
                      <p className="text-sm text-gray-500">Health assessment</p>
                      <p className="font-semibold text-green-800">
                        {getHealthStatus(scan.severity)}
                      </p>
                    </div>

                    <div>
                      <p className="text-sm text-gray-500">Disease stage</p>
                      <p className="font-semibold">{scan.stage ?? "Unavailable"}</p>
                    </div>

                    <div>
                      <p className="text-sm text-gray-500">Scan date</p>
                      <p className="font-semibold">
                        {new Date(scan.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                </article>
              ))
            )}
          </div>
        )}
      </div>
    </main>
  );
}
