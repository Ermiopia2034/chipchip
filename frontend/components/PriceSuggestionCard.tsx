"use client";

import React from "react";
import { TrendingUp } from "lucide-react";

type Row = { label: string; value: number | null };

export default function PriceSuggestionCard({
  product,
  rows,
  recommended,
  onAction,
}: {
  product: string;
  rows: Row[];
  recommended: number | null;
  onAction?: (id: string) => void;
}) {
  return (
    <div className="group relative overflow-hidden rounded-2xl border border-black/10 dark:border-white/10 glass p-4">
      <div className="absolute -top-10 -right-10 h-28 w-28 rounded-full bg-[radial-gradient(circle_at_center,hsl(var(--brand-3)/0.18)_0%,transparent_60%)] group-hover:scale-110 transition-transform" />
      <div className="relative z-10">
        <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400 mb-2">
          <TrendingUp className="h-4 w-4" />
          <span className="text-sm font-semibold tracking-tight">Pricing for {product}</span>
        </div>
        <div className="overflow-hidden rounded-xl border border-black/10 dark:border-white/10">
          <table className="w-full text-sm">
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} className="border-b border-black/10 dark:border-white/10 bg-white/70 dark:bg-white/5">
                  <td className="px-3 py-2 text-gray-600 dark:text-gray-300 w-1/2">{r.label}</td>
                  <td className="px-3 py-2 font-medium">{r.value != null ? `${r.value} ETB/kg` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {recommended != null ? (
          <div className="mt-3 text-sm">
            Recommendation: <span className="font-semibold">{recommended} ETB/kg</span>
          </div>
        ) : null}
        <div className="mt-3 flex gap-2">
          {recommended != null ? (
            <button
              className="rounded-xl bg-blue-600 text-white px-3 py-2 text-xs font-medium btn-glow"
              onClick={() => onAction?.("use_recommended")}
            >
              Use {recommended} ETB/kg
            </button>
          ) : null}
          <button
            className="rounded-xl border border-black/10 dark:border-white/15 px-3 py-2 text-xs"
            onClick={() => onAction?.("set_custom")}
          >
            Set custom price…
          </button>
        </div>
      </div>
    </div>
  );
}

