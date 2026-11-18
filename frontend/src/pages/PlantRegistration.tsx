
import { useState, type FormEvent } from "react";
import { Sprout, MapPin, CalendarDays, CheckCircle2 } from "lucide-react";

interface Plant {
  id: number;
  name: string;
  type: string;
  date: string;
  location: string;
}

export default function PlantRegistration() {
  const [plant, setPlant] = useState({
    name: "",
    type: "",
    date: "",
    location: "",
  });

  const [message, setMessage] = useState("");

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const savedPlants: Plant[] = JSON.parse(
      localStorage.getItem("plants") || "[]"
    );

    const newPlant: Plant = {
      id: Date.now(),
      ...plant,
    };

    localStorage.setItem(
      "plants",
      JSON.stringify([...savedPlants, newPlant])
    );

    setPlant({
      name: "",
      type: "",
      date: "",
      location: "",
    });

    setMessage("Plant registered successfully!");
  };

  return (
    <div className="min-h-screen bg-background px-4 py-10">
      <div className="mx-auto max-w-2xl">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-green-100 text-green-700">
            <Sprout size={30} />
          </div>

          <h1 className="text-3xl font-bold">
            Plant Registration
          </h1>

          <p className="mt-2 text-muted-foreground">
            Register your plants and manage their information.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="space-y-5 rounded-xl border bg-card p-6 shadow-sm"
        >
          <div>
            <label className="mb-2 block text-sm font-medium">
              Plant Name
            </label>
            <input
              name="name"
              value={plant.name}
              onChange={(e) => {
                setPlant({ ...plant, name: e.target.value });
                setMessage("");
              }}
              placeholder="Enter plant name"
              required
              className="w-full rounded-lg border bg-background px-4 py-3 outline-none focus:ring-2 focus:ring-green-600"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium">
              Plant Type
            </label>
            <select
              name="type"
              value={plant.type}
              onChange={(e) => {
                setPlant({ ...plant, type: e.target.value });
                setMessage("");
              }}
              required
              className="w-full rounded-lg border bg-background px-4 py-3 outline-none focus:ring-2 focus:ring-green-600"
            >
              <option value="">Select plant type</option>
              <option value="Vegetable">Vegetable</option>
              <option value="Fruit">Fruit</option>
              <option value="Flower">Flower</option>
              <option value="Herb">Herb</option>
              <option value="Other">Other</option>
            </select>
          </div>

          <div>
            <label className="mb-2 flex items-center gap-2 text-sm font-medium">
              <CalendarDays size={17} />
              Planting Date
            </label>
            <input
              type="date"
              name="date"
              value={plant.date}
              onChange={(e) => {
                setPlant({ ...plant, date: e.target.value });
                setMessage("");
              }}
              required
              className="w-full rounded-lg border bg-background px-4 py-3 outline-none focus:ring-2 focus:ring-green-600"
            />
          </div>

          <div>
            <label className="mb-2 flex items-center gap-2 text-sm font-medium">
              <MapPin size={17} />
              Location
            </label>
            <input
              name="location"
              value={plant.location}
              onChange={(e) => {
                setPlant({ ...plant, location: e.target.value });
                setMessage("");
              }}
              placeholder="Enter farm or garden location"
              required
              className="w-full rounded-lg border bg-background px-4 py-3 outline-none focus:ring-2 focus:ring-green-600"
            />
          </div>

          <button
            type="submit"
            className="w-full rounded-lg bg-green-700 px-5 py-3 font-semibold text-white transition hover:bg-green-800"
          >
            <span className="inline-flex items-center gap-2">
              <Sprout size={19} />
              Register Plant
            </span>
          </button>

          {message && (
            <p className="flex items-center justify-center gap-2 text-sm font-medium text-green-700">
              <CheckCircle2 size={18} />
              {message}
            </p>
          )}
        </form>
      </div>
    </div>
  );
}
