import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { History, Package, ShoppingBag } from "lucide-react";
import { api } from "@/lib/api";

export default function OrderHistoryPage() {
  const { data: orders, isLoading, isError } = useQuery({
    queryKey: ["orders"],
    queryFn: () => api.getOrders(),
  });

  if (isLoading) {
    return <div className="mx-auto max-w-5xl p-8">Loading your orders...</div>;
  }

  if (isError) {
    return <div className="mx-auto max-w-5xl p-8">Unable to load your orders. Please sign in and try again.</div>;
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-8 flex items-center gap-3">
        <History className="h-8 w-8 text-green-600" />
        <div>
          <h1 className="text-2xl font-bold">My Orders</h1>
          <p className="text-sm text-muted-foreground">View your previous purchases and order details.</p>
        </div>
      </div>

      {!orders?.length ? (
        <div className="rounded-xl border p-10 text-center">
          <Package className="mx-auto mb-4 h-12 w-12 text-gray-400" />
          <h2 className="text-xl font-semibold">No orders yet</h2>
          <p className="mt-2 text-muted-foreground">Your completed purchases will appear here.</p>
          <Link to="/marketplace/products" className="mt-5 inline-flex items-center gap-2 rounded-lg bg-green-600 px-5 py-3 text-white">
            <ShoppingBag className="h-4 w-4" /> Browse Products
          </Link>
        </div>
      ) : (
        <div className="space-y-5">
          {orders.map((order) => (
            <section key={order.id} className="rounded-xl border p-5 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-4">
                <div>
                  <h2 className="font-semibold">Order #{order.id}</h2>
                  <p className="text-sm text-muted-foreground">
                    {new Date(order.created_at).toLocaleString()}
                  </p>
                </div>
                <span className="rounded-full bg-green-100 px-3 py-1 text-sm font-medium capitalize text-green-800">
                  {order.status}
                </span>
              </div>

              <div className="space-y-3 py-4">
                {order.items.map((item, index) => (
                  <div key={`${item.product_id}-${index}`} className="flex flex-wrap justify-between gap-2 text-sm">
                    <div>
                      <p className="font-medium">{item.product_name}</p>
                      <p className="text-muted-foreground">
                        Quantity: {item.quantity} × ?{item.unit_price}
                      </p>
                    </div>
                    <p className="font-semibold">?{item.subtotal.toFixed(2)}</p>
                  </div>
                ))}
              </div>

              <div className="border-t pt-4">
                <p className="text-sm text-muted-foreground">Delivery Address</p>
                <p className="mt-1 text-sm">{order.shipping_address}</p>
                <p className="mt-4 text-right text-lg font-bold">
                  Total: ?{order.total_amount.toFixed(2)}
                </p>
              </div>
            </section>
          ))}
        </div>
      )}
    </main>
  );
}
