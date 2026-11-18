import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { Package, ShoppingBag } from "lucide-react";

export default function OrderHistory() {
  const { data: orders = [], isLoading, isError } = useQuery({
    queryKey: ["orders"],
    queryFn: () => api.getOrders(),
  });

  if (isLoading) {
    return <div className="container mx-auto p-6">Loading your orders...</div>;
  }

  if (isError) {
    return <div className="container mx-auto p-6 text-red-600">
      Unable to load orders. Please try again.
    </div>;
  }

  return (
    <main className="container mx-auto max-w-5xl p-4 sm:p-6">
      <div className="mb-8 flex items-center gap-3">
        <Package className="h-8 w-8 text-green-700" />
        <div>
          <h1 className="text-3xl font-bold">Order History</h1>
          <p className="text-muted-foreground">View and track your purchases.</p>
        </div>
      </div>

      {orders.length === 0 ? (
        <div className="rounded-xl border p-10 text-center">
          <ShoppingBag className="mx-auto mb-4 h-12 w-12 text-gray-400" />
          <h2 className="text-xl font-semibold">No orders yet</h2>
          <p className="my-3 text-gray-500">Your purchases will appear here.</p>
          <Link to="/shop" className="inline-block rounded-lg bg-green-700 px-5 py-3 text-white">
            Browse Products
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map((order) => (
            <section key={order.id} className="rounded-xl border p-5 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="font-semibold">Order #{order.id}</h2>
                  <p className="text-sm text-gray-500">
                    {new Date(order.created_at).toLocaleString()}
                  </p>
                </div>
                <span className="rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800">
                  {order.status}
                </span>
              </div>
              <div className="mt-4 flex flex-wrap justify-between gap-3 border-t pt-4">
                <div>
                  <p className="text-sm text-gray-500">Shipping address</p>
                  <p>{order.shipping_address}</p>
                </div>
                <div className="font-semibold">
                  Total: ₹{Number(order.total_amount).toFixed(2)}
                </div>
              </div>
            </section>
          ))}
        </div>
      )}
    </main>
  );
}
