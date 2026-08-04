import { useEffect } from "react";
import { RouterProvider } from "react-router-dom";

import { Providers } from "@/app/providers";
import { router } from "@/app/router";
import { useAuth } from "@/stores/auth";

export default function App() {
  const hydrate = useAuth((state) => state.hydrate);

  // Restore a stored session (token in localStorage) on boot.
  useEffect(() => {
    void hydrate();
  }, [hydrate]);

  return (
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  );
}
