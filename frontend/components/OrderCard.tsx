"use client";

import React from "react";

type OrderItem = { product_id?: number; product_name?: string; quantity_kg: number; price_per_unit: number };
type Order = { items: OrderItem[]; total: number; delivery_date: string; delivery_location: string };

export default function OrderCard({ order }: { order: Order }) {
  return (
    <div className="rounded-2xl border border-black/10 dark:border-white/10 glass p-4">
      <div className="font-semibold text-sm tracking-tight">Order Summary</div>
      <div className="text-sm text-gray-600 dark:text-gray-300">Delivery: {order.delivery_date} → {order.delivery_location}</div>
      <ul className="mt-2 text-sm list-disc pl-5">
        {order.items.map((it, i) => (
          <li key={i}>{it.quantity_kg} kg {it.product_name || `#${it.product_id}`} @ {it.price_per_unit} ETB/kg</li>
        ))}
      </ul>
      <div className="mt-2 font-medium">Total: {order.total} ETB</div>
    </div>
  );
}
