
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ShoppingCart, Trash2 } from "lucide-react";
import { api } from "@/lib/api";

export default function Cart() {
  const queryClient = useQueryClient();
  const [shippingAddress, setShippingAddress] = useState("");
  const [orderMessage, setOrderMessage] = useState("");

  const { data: cart, isLoading, isError } = useQuery({
    queryKey: ["cart"],
    queryFn: () => api.getCart(),
  });

  const removeMutation = useMutation({
    mutationFn: (itemId: number) => api.removeFromCart(itemId),
    onSuccess: (updatedCart) => {
      queryClient.setQueryData(["cart"], updatedCart);
    },
  });

  const checkoutMutation = useMutation({
    mutationFn: () => api.checkout(shippingAddress),
    onSuccess: async (order) => {
      await queryClient.invalidateQueries({ queryKey: ["cart"] });
      setOrderMessage(`Order placed successfully! Order ID: ${order.id}`);
      setShippingAddress("");
    },
    onError: () => {
      setOrderMessage("Unable to place order. Please try again.");
    },
  });

  if (isLoading) {
    return <div className="mx-auto max-w-5xl p-8">Loading your cart...</div>;
  }

  if (isError) {
    return (
      <div className="mx-auto max-w-5xl p-8 text-center">
        Unable to load your cart. Please sign in and try again.
      </div>
    );
  }

  const items = cart?.items ?? [];

  if (items.length === 0) {
    return (
      <div className="mx-auto max-w-4xl p-12 text-center">
        <ShoppingCart className="mx-auto mb-4 h-16 w-16 text-gray-400" />
        <h1 className="text-2xl font-bold">Your Cart is Empty</h1>
        <p className="mt-2 text-gray-500">
          Browse Agri Store and add products to your cart.
        </p>
        <Link
          to="/marketplace/products"
          className="mt-6 inline-block rounded-lg bg-green-600 px-6 py-3 text-white"
        >
          Continue Shopping
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <h1 className="mb-6 text-2xl font-bold">
        Shopping Cart ({items.length} items)
      </h1>

      <div className="space-y-4">
        {items.map((item) => (
          <div
            key={item.id}
            className="flex flex-wrap items-center justify-between gap-4 rounded-lg border p-4"
          >
            <div className="flex items-center gap-4">
              {item.product.images?.[0] && (
                <img
                  src={item.product.images[0]}
                  alt={item.product.name}
                  className="h-20 w-20 rounded-lg object-cover"
                />
              )}

              <div>
                <h2 className="font-semibold">{item.product.name}</h2>
                <p className="text-sm text-gray-600">
                  Price: ₹{item.product.price}
                </p>
                <p className="text-sm text-gray-600">
                  Quantity: {item.quantity}
                </p>
                <p className="font-semibold">
                  Subtotal: ₹{item.subtotal}
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => removeMutation.mutate(item.id)}
              disabled={removeMutation.isPending}
              className="flex items-center gap-2 rounded-lg border border-red-300 px-3 py-2 text-red-600 hover:bg-red-50 disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" />
              Remove
            </button>
          </div>
        ))}
      </div>

      <div className="mt-6 rounded-lg border p-5 text-right">
        <p className="text-xl font-bold">
          Total: ₹{cart?.total_amount ?? 0}
        </p>

        <Link
          to="/marketplace/products"
          className="mt-4 inline-block rounded-lg border px-5 py-3"
        >
          Continue Shopping
        </Link>
      </div>

      <div className="mt-6 rounded-lg border p-5">
        <h2 className="mb-3 text-lg font-bold">Shipping Address</h2>

        <textarea
          value={shippingAddress}
          onChange={(event) => setShippingAddress(event.target.value)}
          placeholder="Enter your complete delivery address"
          className="w-full rounded-lg border p-3"
          rows={3}
        />

        <button
          type="button"
          disabled={
            !shippingAddress.trim() ||
            checkoutMutation.isPending ||
            items.length === 0
          }
          onClick={() => {
            setOrderMessage("");
            checkoutMutation.mutate();
          }}
          className="mt-4 rounded-lg bg-green-600 px-6 py-3 text-white disabled:opacity-50"
        >
          {checkoutMutation.isPending ? "Placing Order..." : "Place Order"}
        </button>

        {orderMessage && (
          <p className="mt-3" role="status">
            {orderMessage}
          </p>
        )}
      </div>
    </div>
  );
}
