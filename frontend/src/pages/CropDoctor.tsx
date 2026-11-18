
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import {
  Activity,
  Stethoscope,
  Loader2,
} from "lucide-react";

export default function CropDoctor() {
  const [scanId, setScanId] = useState("");
  const [selectedScanId, setSelectedScanId] = useState<number | null>(null);

  const scanQuery = useQuery({
    queryKey: ["crop-doctor-scan", selectedScanId],
    queryFn: () => api.getScan(selectedScanId!),
    enabled: selectedScanId !== null,
  });

  const explanationQuery = useQuery({
    queryKey: ["crop-doctor-explanation", selectedScanId],
    queryFn: () => api.getScanExplain(selectedScanId!),
    enabled: selectedScanId !== null,
  });

  const recommendationQuery = useQuery({
    queryKey: ["crop-doctor-recommendations", selectedScanId],
    queryFn: () => api.getScanRecommendations(selectedScanId!),
    enabled: selectedScanId !== null,
  });

  function handleSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const id = Number(scanId);

    if (Number.isInteger(id) && id > 0) {
      setSelectedScanId(id);
    }
  }

  const scan = scanQuery.data;

  return (
    <main className="min-h-screen bg-green-50 px-4 py-8">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8 flex items-center gap-3">
          <div className="rounded-xl bg-green-700 p-3 text-white">
            <Stethoscope size={28} />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-green-900">
              Crop Doctor
            </h1>
            <p className="text-gray-600">
              Understand plant diseases and find ways to treat them.
            </p>
          </div>
        </div>

        <form
          onSubmit={handleSearch}
          className="mb-6 flex flex-col gap-3 rounded-xl bg-white p-5 shadow-sm sm:flex-row"
        >
          <input
            type="number"
            min="1"
            value={scanId}
            onChange={(event) => setScanId(event.target.value)}
            placeholder="Enter AI Scan ID"
            className="min-w-0 flex-1 rounded-lg border p-3"
            required
          />
          <button
            type="submit"
            className="rounded-lg bg-green-700 px-6 py-3 font-semibold text-white hover:bg-green-800"
          >
            Check Plant Health
          </button>
        </form>

        {scanQuery.isLoading && (
          <p className="flex items-center gap-2 text-green-800">
            <Loader2 className="animate-spin" /> Loading scan...
          </p>
        )}

        {scanQuery.isError && (
          <p className="rounded-lg bg-red-100 p-4 text-red-700">
            Could not load this scan. Check the scan ID and try again.
          </p>
        )}

        {scan && (
          <section className="space-y-5">
            <div className="rounded-xl bg-white p-6 shadow-sm">
              <h2 className="mb-4 flex items-center gap-2 text-xl font-bold text-green-900">
                <Activity /> AI Disease Report
              </h2>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm text-gray-500">Detected disease</p>
                  <p className="font-semibold text-gray-900">
                    {scan.disease_name || "Not identified"}
                  </p>
                </div>

                <div>
                  <p className="text-sm text-gray-500">Confidence</p>
                  <p className="font-semibold text-gray-900">
                    {(scan.confidence * 100).toFixed(2)}%
                  </p>
                </div>

                <div>
                  <p className="text-sm text-gray-500">Severity</p>
                  <p className="font-semibold text-gray-900">
                    {scan.severity ?? "Not available"}
                  </p>
                </div>

                <div>
                  <p className="text-sm text-gray-500">Disease stage</p>
                  <p className="font-semibold text-gray-900">
                    {scan.stage ?? "Not available"}
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-xl bg-white p-6 shadow-sm">
              <h2 className="mb-3 text-xl font-bold text-green-900">
                Disease Explanation
              </h2>

              {explanationQuery.isLoading ? (
                <p>Loading explanation...</p>
              ) : explanationQuery.isError ? (
                <p className="text-amber-700">
                  Explanation is currently unavailable.
                </p>
              ) : (
                <pre className="whitespace-pre-wrap break-words font-sans text-gray-700">
                  {JSON.stringify(explanationQuery.data, null, 2)}
                </pre>
              )}
            </div>

            <div className="rounded-xl bg-white p-6 shadow-sm">
              <h2 className="mb-3 text-xl font-bold text-green-900">
                Treatment and Recommendations
              </h2>

              {recommendationQuery.isLoading ? (
                <p>Loading recommendations...</p>
              ) : recommendationQuery.isError ? (
                <p className="text-amber-700">
                  Recommendations are currently unavailable.
                </p>
              ) : (
                <pre className="whitespace-pre-wrap break-words font-sans text-gray-700">
                  {JSON.stringify(recommendationQuery.data, null, 2)}
                </pre>
              )}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
