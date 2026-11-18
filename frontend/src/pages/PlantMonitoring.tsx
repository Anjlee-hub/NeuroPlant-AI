
import { useEffect, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { api } from "@/lib/api";
import type { Scan } from "@/types/scan";
import {
  Activity,
  Sprout,
  ImagePlus,
  TrendingUp,
  Trash2,
  FileText,
  HeartPulse,
  AlertCircle,
} from "lucide-react";

interface Plant {
  id: number;
  name: string;
  type: string;
  date: string;
  location: string;
}

interface ProgressEntry {
  id: number;
  plantId: number;
  date: string;
  condition: string;
  notes: string;
}

export default function PlantMonitoring() {
  const [plants, setPlants] = useState<Plant[]>([]);
  const [progress, setProgress] = useState<ProgressEntry[]>([]);
  const [selectedPlant, setSelectedPlant] = useState("");
  const [beforeImage, setBeforeImage] = useState("");
  const [afterImage, setAfterImage] = useState("");
  const [afterFile, setAfterFile] = useState<File | null>(null);
  const [scanning, setScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState("");
  const [scanResult, setScanResult] = useState<Scan | null>(null);
  const [condition, setCondition] = useState("Stable");
  const [notes, setNotes] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    try {
      const savedPlants = JSON.parse(
        localStorage.getItem("plants") || "[]"
      ) as Plant[];

      const savedProgress = JSON.parse(
        localStorage.getItem("plantProgress") || "[]"
      ) as ProgressEntry[];

      setPlants(savedPlants);
      setProgress(savedProgress);

      if (savedPlants.length > 0) {
        setSelectedPlant(String(savedPlants[0].id));
      }
    } catch {
      setPlants([]);
      setProgress([]);
    }
  }, []);

  const handleImage = (
    e: ChangeEvent<HTMLInputElement>,
    type: "before" | "after"
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setMessage("Please select a valid image.");
      return;
    }

    const imageUrl = URL.createObjectURL(file);

    if (type === "before") {
      if (beforeImage) URL.revokeObjectURL(beforeImage);
      setBeforeImage(imageUrl);
    } else {
      if (afterImage) URL.revokeObjectURL(afterImage);
      setAfterImage(imageUrl);
      setAfterFile(file);
      setScanResult(null);
      setScanMessage("");
    }

    setMessage("");
  };

  const handleScan = async () => {
    if (!afterFile) {
      setScanMessage("Please upload a recent plant image.");
      return;
    }

    setScanning(true);
    setScanMessage("Scanning plant image...");

    try {
      const result = await api.uploadScan({
        files: [afterFile],
        clientScanId: crypto.randomUUID(),
      });

      setScanResult(result);
      setScanMessage("Plant scan completed successfully!");
    } catch (error) {
      setScanMessage(
        error instanceof Error ? error.message : "Scan failed."
      );
    } finally {
      setScanning(false);
    }
  };

  const handleProgress = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!selectedPlant) {
      setMessage("Please register a plant first.");
      return;
    }

    const entry: ProgressEntry = {
      id: Date.now(),
      plantId: Number(selectedPlant),
      date: new Date().toISOString().slice(0, 10),
      condition,
      notes,
    };

    const updated = [...progress, entry];

    setProgress(updated);
    localStorage.setItem("plantProgress", JSON.stringify(updated));

    setNotes("");
    setMessage("Progress saved successfully!");
  };

  const deleteProgress = (id: number) => {
    const updated = progress.filter((entry) => entry.id !== id);
    setProgress(updated);
    localStorage.setItem("plantProgress", JSON.stringify(updated));
  };

  const selectedPlantData = plants.find(
    (plant) => plant.id === Number(selectedPlant)
  );

  const selectedPlantProgress = progress
    .filter((entry) => entry.plantId === Number(selectedPlant))
    .sort((a, b) => b.date.localeCompare(a.date));

  const getHealthStatus = () => {
    if (!scanResult) return "Awaiting AI scan";

    const severity = scanResult.severity?.toLowerCase() || "";

    if (severity.includes("severe")) return "Needs urgent attention";
    if (severity.includes("moderate")) return "Needs treatment";
    if (severity.includes("mild")) return "Mild symptoms detected";

    if (
      scanResult.disease_name.toLowerCase().includes("healthy") ||
      scanResult.disease_name.toLowerCase().includes("no disease")
    ) {
      return "No disease detected";
    }

    return "Review AI diagnosis";
  };

  const getHealthColor = () => {
    const status = getHealthStatus();

    if (status === "No disease detected") {
      return "bg-green-100 text-green-800";
    }

    if (status === "Needs urgent attention") {
      return "bg-red-100 text-red-800";
    }

    if (status === "Needs treatment" || status === "Mild symptoms detected") {
      return "bg-yellow-100 text-yellow-800";
    }

    return "bg-gray-100 text-gray-700";
  };

  return (
    <div className="min-h-screen bg-background px-4 py-10">
      <div className="mx-auto max-w-5xl">

        <div className="mb-8 text-center">
          <Activity size={35} className="mx-auto mb-3 text-green-700" />
          <h1 className="text-3xl font-bold">Plant Monitoring</h1>
          <p className="mt-2 text-muted-foreground">
            Monitor plant health and track disease progression.
          </p>
        </div>

        {plants.length === 0 ? (
          <div className="rounded-xl border bg-card p-8 text-center">
            <Sprout size={40} className="mx-auto mb-3 text-green-700" />
            <h2 className="text-xl font-semibold">
              No Plants Registered
            </h2>
            <p className="mt-2 text-muted-foreground">
              Please register a plant before monitoring.
            </p>
          </div>
        ) : (
          <>
            <section className="mb-6 rounded-xl border bg-card p-5">
              <label className="mb-2 block font-semibold">
                Select Plant
              </label>

              <select
                value={selectedPlant}
                onChange={(e) => {
                  setSelectedPlant(e.target.value);
                  setScanResult(null);
                  setScanMessage("");
                  setBeforeImage("");
                  setAfterImage("");
                  setAfterFile(null);
                }}
                className="w-full rounded-lg border bg-background p-3"
              >
                {plants.map((plant) => (
                  <option key={plant.id} value={plant.id}>
                    {plant.name} ({plant.type})
                  </option>
                ))}
              </select>
            </section>

            {/* BEFORE AND AFTER IMAGE COMPARISON */}
            <section className="mb-6 rounded-xl border bg-card p-6">
              <h2 className="mb-4 flex items-center gap-2 text-xl font-bold">
                <ImagePlus className="text-green-700" />
                Before and After Image Comparison
              </h2>

              <div className="grid gap-6 md:grid-cols-2">
                <div>
                  <label className="mb-2 block font-medium">
                    Before Image
                  </label>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => handleImage(e, "before")}
                  />
                  {beforeImage && (
                    <img
                      src={beforeImage}
                      alt="Before plant"
                      className="mt-4 h-60 w-full rounded-lg border object-cover"
                    />
                  )}
                </div>

                <div>
                  <label className="mb-2 block font-medium">
                    After Image
                  </label>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => handleImage(e, "after")}
                  />
                  {afterImage && (
                    <img
                      src={afterImage}
                      alt="After plant"
                      className="mt-4 h-60 w-full rounded-lg border object-cover"
                    />
                  )}
                </div>
              </div>

              <button
                type="button"
                onClick={handleScan}
                disabled={scanning || !afterFile}
                className="mt-5 rounded-lg bg-green-700 px-6 py-3 font-semibold text-white hover:bg-green-800 disabled:opacity-50"
              >
                {scanning ? "Scanning..." : "Scan Plant"}
              </button>

              {scanMessage && (
                <p className="mt-3 text-sm text-green-700">
                  {scanMessage}
                </p>
              )}

              {scanResult && (
                <div className="mt-5 rounded-xl border border-green-200 bg-green-50 p-5">
                  <h3 className="mb-3 text-xl font-bold text-green-800">
                    AI Disease Detection Result
                  </h3>

                  <div className="space-y-2 text-gray-700">
                    <p><strong>Scan ID:</strong> {scanResult.id}</p>
                    <p><strong>Disease:</strong> {scanResult.disease_name}</p>
                    <p>
                      <strong>Confidence:</strong>{" "}
                      {(scanResult.confidence * 100).toFixed(2)}%
                    </p>
                    <p>
                      <strong>Severity:</strong>{" "}
                      {scanResult.severity ?? "Not available"}
                    </p>
                    <p>
                      <strong>Disease Stage:</strong>{" "}
                      {scanResult.stage ?? "Not available"}
                    </p>
                    <p>
                      <strong>AI Model:</strong>{" "}
                      {scanResult.model_name ?? "Not available"}
                    </p>
                    <p>
                      <strong>Scan Date:</strong>{" "}
                      {new Date(scanResult.created_at).toLocaleString()}
                    </p>
                  </div>

                  {scanResult.rankings.length > 0 && (
                    <div className="mt-4 border-t border-green-200 pt-4">
                      <h4 className="mb-2 font-semibold">
                        Other Possible Diseases
                      </h4>

                      {scanResult.rankings.map((item, index) => (
                        <p key={index} className="text-sm text-gray-700">
                          {index + 1}. {item.disease_name} —{" "}
                          {(item.confidence * 100).toFixed(2)}%
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </section>

            {/* PLANT HEALTH REPORT */}
            <section className="mb-6 rounded-xl border bg-card p-6">
              <h2 className="mb-5 flex items-center gap-2 text-xl font-bold">
                <FileText className="text-green-700" />
                Plant Health Report
              </h2>

              {scanResult ? (
                <>
                  <div className="mb-5 rounded-xl bg-green-50 p-5">
                    <div className="mb-3 flex items-center gap-2">
                      <HeartPulse className="text-green-700" />
                      <h3 className="text-lg font-bold text-green-900">
                        Health Assessment
                      </h3>
                    </div>

                    <span
                      className={`inline-block rounded-full px-4 py-2 text-sm font-semibold ${getHealthColor()}`}
                    >
                      {getHealthStatus()}
                    </span>

                    <p className="mt-3 text-sm text-gray-700">
                      This assessment is based on the latest AI scan.
                    </p>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="rounded-lg border p-4">
                      <p className="text-sm text-muted-foreground">
                        Plant Name
                      </p>
                      <p className="font-semibold">
                        {selectedPlantData?.name}
                      </p>
                    </div>

                    <div className="rounded-lg border p-4">
                      <p className="text-sm text-muted-foreground">
                        Plant Type
                      </p>
                      <p className="font-semibold">
                        {selectedPlantData?.type}
                      </p>
                    </div>

                    <div className="rounded-lg border p-4">
                      <p className="text-sm text-muted-foreground">
                        Detected Disease
                      </p>
                      <p className="font-semibold">
                        {scanResult.disease_name}
                      </p>
                    </div>

                    <div className="rounded-lg border p-4">
                      <p className="text-sm text-muted-foreground">
                        Disease Severity
                      </p>
                      <p className="font-semibold">
                        {scanResult.severity ?? "Not available"}
                      </p>
                    </div>

                    <div className="rounded-lg border p-4">
                      <p className="text-sm text-muted-foreground">
                        Disease Stage
                      </p>
                      <p className="font-semibold">
                        {scanResult.stage ?? "Not available"}
                      </p>
                    </div>

                    <div className="rounded-lg border p-4">
                      <p className="text-sm text-muted-foreground">
                        AI Confidence
                      </p>
                      <p className="font-semibold">
                        {(scanResult.confidence * 100).toFixed(2)}%
                      </p>
                    </div>

                    <div className="rounded-lg border p-4">
                      <p className="text-sm text-muted-foreground">
                        Report Date
                      </p>
                      <p className="font-semibold">
                        {new Date(scanResult.created_at).toLocaleString()}
                      </p>
                    </div>

                    <div className="rounded-lg border p-4">
                      <p className="text-sm text-muted-foreground">
                        Scan Status
                      </p>
                      <p className="font-semibold">
                        {scanResult.sync_status}
                      </p>
                    </div>
                  </div>
                </>
              ) : (
                <div className="rounded-lg bg-muted/40 p-6 text-center">
                  <AlertCircle className="mx-auto mb-2 text-green-700" />
                  <p className="font-medium">
                    No AI health report available yet.
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Upload a recent plant image and click Scan Plant to
                    generate your health report.
                  </p>
                </div>
              )}
            </section>

            {/* DISEASE PROGRESSION */}
            <section className="mb-6 rounded-xl border bg-card p-6">
              <h2 className="mb-4 flex items-center gap-2 text-xl font-bold">
                <TrendingUp className="text-green-700" />
                Disease Progression
              </h2>

              <form onSubmit={handleProgress} className="space-y-4">
                <div>
                  <label className="mb-2 block font-medium">
                    Plant Condition
                  </label>
                  <select
                    value={condition}
                    onChange={(e) => setCondition(e.target.value)}
                    className="w-full rounded-lg border bg-background p-3"
                  >
                    <option>Improving</option>
                    <option>Stable</option>
                    <option>Worsening</option>
                    <option>Symptoms Observed</option>
                  </select>
                </div>

                <div>
                  <label className="mb-2 block font-medium">
                    Symptoms and Observations
                  </label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Describe plant symptoms..."
                    required
                    rows={3}
                    className="w-full rounded-lg border bg-background p-3"
                  />
                </div>

                <button
                  type="submit"
                  className="w-full rounded-lg bg-green-700 px-5 py-3 font-semibold text-white hover:bg-green-800"
                >
                  Save Progress
                </button>
              </form>

              {message && (
                <p className="mt-3 text-sm text-green-700">
                  {message}
                </p>
              )}
            </section>

            {/* MONITORING HISTORY */}
            <section className="rounded-xl border bg-card p-6">
              <h2 className="mb-5 text-xl font-bold">
                Monitoring History
              </h2>

              {selectedPlantProgress.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No progress records available.
                </p>
              ) : (
                <div className="space-y-4">
                  {selectedPlantProgress.map((entry) => (
                    <div
                      key={entry.id}
                      className="rounded-lg border-l-4 border-green-600 bg-muted/40 p-4"
                    >
                      <div className="flex justify-between gap-3">
                        <strong>{entry.condition}</strong>
                        <span className="text-sm text-muted-foreground">
                          {entry.date}
                        </span>
                      </div>

                      <p className="mt-2 text-sm">{entry.notes}</p>

                      <button
                        type="button"
                        onClick={() => deleteProgress(entry.id)}
                        className="mt-3 flex items-center gap-2 text-sm text-red-600"
                      >
                        <Trash2 size={15} />
                        Delete
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}
