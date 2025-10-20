"use client";

import React from "react";
import { AlertTriangle, Zap } from "lucide-react";

export default function NudgeCard({
  title,
  suggestions,
  onAction,
}: {
  title: string;
  suggestions: { name: string; qty: string; days: number; discount: number }[];
  onAction?: (id: string) => void;
}) {
  return (
    <div className="rounded-2xl border border-amber-300/50 bg-amber-50 text-amber-900 dark:bg-amber-950/30 dark:text-amber-200 p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-2">
        <AlertTriangle className="h-4 w-4" />
        <span className="font-semibold text-sm">{title}</span>
      </div>
      <ul className="text-sm list-disc pl-5">
        {suggestions.map((s, i) => (
          <li key={i}>
            {s.name} ({s.qty}) — Expires in {s.days} day{s.days === 1 ? "" : "s"}. Suggest {s.discount}% off.
          </li>
        ))}
      </ul>
      <div className="mt-3">
        <button
          className="inline-flex items-center gap-2 rounded-xl bg-amber-500 text-white px-3 py-2 text-xs font-medium"
          onClick={() => onAction?.("run_flash_sale")}
        >
          <Zap className="h-3 w-3" /> Run suggested flash sale
        </button>
      </div>
    </div>
  );
}

