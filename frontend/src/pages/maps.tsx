
import { useState } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
} from "react-leaflet";

type Service = {
  id: number;
  name: string;
  category: string;
  latitude: number;
  longitude: number;
  distance: number;
};

function calculateDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) ** 2;

  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function getCategory(tags: Record<string, string>) {
  const shop = (tags.shop || "").toLowerCase();

  const categories: Record<string, string> = {
    agrarian: "Agricultural Supply Store",
    seeds: "Seed Shop",
    fertilizer: "Fertilizer Shop",
    agricultural_machinery: "Farm Equipment Store",
  };

  return categories[shop] || "Agricultural Service";
}

async function findNearbyServices(lat: number, lon: number) {
  const query = `
    [out:json][timeout:25];
    (
      nwr(around:10000,${lat},${lon})["shop"~"^(agrarian|seeds|fertilizer|agricultural_machinery)$"];
    );
    out center tags;
  `;

  const response = await fetch(
    "https://overpass-api.de/api/interpreter",
    {
      method: "POST",
      body: new URLSearchParams({ data: query }),
    }
  );

  if (!response.ok) {
    throw new Error("Could not load nearby agricultural services.");
  }

  const data = await response.json();

  return data.elements
    .filter((item: any) => item.tags?.name)
    .map((item: any) => {
      const latitude = item.lat ?? item.center?.lat;
      const longitude = item.lon ?? item.center?.lon;

      if (latitude == null || longitude == null) return null;

      return {
        id: item.id,
        name: item.tags.name,
        category: getCategory(item.tags),
        latitude,
        longitude,
        distance: calculateDistance(lat, lon, latitude, longitude),
      };
    })
    .filter((item: Service | null): item is Service => item !== null)
    .filter(
      (service: Service, index: number, all: Service[]) =>
        all.findIndex(
          (item) =>
            item.name.toLowerCase() === service.name.toLowerCase() &&
            Math.abs(item.latitude - service.latitude) < 0.0001 &&
            Math.abs(item.longitude - service.longitude) < 0.0001
        ) === index
    )
    .sort((a: Service, b: Service) => a.distance - b.distance);
}

export default function Maps() {
  const [location, setLocation] = useState<{
    latitude: number;
    longitude: number;
  } | null>(null);

  const [services, setServices] = useState<Service[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);

  const getLocation = () => {
    setError("");
    setServices([]);

    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser.");
      return;
    }

    setLoading(true);

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;

        setLocation({ latitude: lat, longitude: lon });
        setLoading(false);
        setSearching(true);

        try {
          const results = await findNearbyServices(lat, lon);
          setServices(results);
        } catch {
          setError(
            "Unable to load nearby services. Please try again later."
          );
        } finally {
          setSearching(false);
        }
      },
      () => {
        setError(
          "Unable to access your location. Please allow location permission."
        );
        setLoading(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="mx-auto max-w-6xl">
        <h1 className="mb-2 text-3xl font-bold text-green-800">
          Agricultural Services Map
        </h1>

        <p className="mb-6 text-gray-600">
          Find your location and explore nearby agricultural services.
        </p>

        <button
          onClick={getLocation}
          disabled={loading || searching}
          className="mb-5 rounded-lg bg-green-700 px-5 py-3 font-semibold text-white hover:bg-green-800 disabled:opacity-50"
        >
          {loading
            ? "Getting location..."
            : searching
              ? "Searching nearby services..."
              : "Find My Location"}
        </button>

        {error && (
          <p className="mb-4 rounded-lg bg-red-100 p-3 text-red-700">
            {error}
          </p>
        )}

        {location && (
          <div className="mb-5 rounded-lg bg-green-100 p-4 text-green-900">
            <h2 className="font-semibold">Your Current Location</h2>
            <p>Latitude: {location.latitude.toFixed(6)}</p>
            <p>Longitude: {location.longitude.toFixed(6)}</p>
          </div>
        )}

        <div className="mb-6 overflow-hidden rounded-xl border bg-white shadow">
          {location ? (
            <MapContainer
              center={[location.latitude, location.longitude]}
              zoom={13}
              style={{ height: "450px", width: "100%" }}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              <CircleMarker
                center={[location.latitude, location.longitude]}
                radius={10}
                pathOptions={{
                  color: "blue",
                  fillColor: "blue",
                  fillOpacity: 1,
                }}
              >
                <Popup>Your Current Location</Popup>
              </CircleMarker>

              {services.map((service) => (
                <CircleMarker
                  key={service.id}
                  center={[service.latitude, service.longitude]}
                  radius={8}
                  pathOptions={{
                    color: "green",
                    fillColor: "green",
                    fillOpacity: 0.8,
                  }}
                >
                  <Popup>
                    <strong>{service.name}</strong>
                    <br />
                    {service.category}
                    <br />
                    Distance: {service.distance.toFixed(2)} km
                  </Popup>
                </CircleMarker>
              ))}
            </MapContainer>
          ) : (
            <div className="flex h-[450px] items-center justify-center bg-gray-100 text-center text-gray-600">
              Click "Find My Location" to display the map.
            </div>
          )}
        </div>

        {location && (
          <section>
            <h2 className="mb-4 text-2xl font-bold text-green-800">
              Nearby Agricultural Services
            </h2>

            {searching && (
              <p className="text-gray-600">
                Searching for agricultural services within 10 km...
              </p>
            )}

            {!searching && services.length === 0 && !error && (
              <p className="rounded-lg bg-yellow-100 p-4 text-yellow-800">
                No agricultural services were found nearby. Try again later
                or check another location.
              </p>
            )}

            <div className="grid gap-4 md:grid-cols-2">
              {services.map((service) => (
                <div
                  key={service.id}
                  className="rounded-xl border bg-white p-4 shadow-sm"
                >
                  <h3 className="font-bold text-green-800">
                    {service.name}
                  </h3>
                  <p className="text-gray-600">{service.category}</p>
                  <p className="mt-2 text-sm text-gray-700">
                    Distance: {service.distance.toFixed(2)} km
                  </p>
                  <a
                    href={`https://www.openstreetmap.org/?mlat=${service.latitude}&mlon=${service.longitude}#map=17/${service.latitude}/${service.longitude}`}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 inline-block font-semibold text-blue-700 hover:underline"
                  >
                    View on Map
                  </a>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
