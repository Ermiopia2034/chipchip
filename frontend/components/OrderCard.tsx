"use client";

import React from "react";

type OrderItem = { product_id?: number; product_name?: string; quantity_kg: number | null; price_per_unit: number | null };
type Order = { items: OrderItem[]; total: number; delivery_date: string; delivery_location: string; payment?: string; order_id?: string };

export default function OrderCard({ order }: { order: Order }) {
  return (
    <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-white/75 dark:bg-white/5 p-4">
      <div className="font-semibold text-sm tracking-tight">Order Summary</div>
      {order.order_id ? (
        <div className="text-xs text-gray-500 dark:text-gray-400 break-all">Order ID: {order.order_id}</div>
      ) : null}
      <div className="text-sm text-gray-600 dark:text-gray-300">Delivery: {order.delivery_date} → {order.delivery_location}</div>
      <ul className="mt-2 text-sm list-disc pl-5">
        {order.items.map((it, i) => (
          <li key={i}>{(it.quantity_kg ?? 0)} kg {it.product_name || `#${it.product_id}`} @ {(it.price_per_unit ?? 0)} ETB/kg</li>
        ))}
      </ul>
      <div className="mt-2 font-medium">Total: {order.total} ETB</div>
      {order.payment ? (
        <div className="text-sm text-gray-600 dark:text-gray-300">Payment: {order.payment}</div>
      ) : null}
    </div>
  );
}
