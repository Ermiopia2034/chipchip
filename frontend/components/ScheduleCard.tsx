"use client";

import React from "react";
import { CalendarDays } from "lucide-react";

export default function ScheduleCard({ entries }: { entries: { when: string; count: number; total: number }[] }) {
  return (
    <div className="rounded-2xl border border-black/10 dark:border-white/10 glass p-4">
      <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400 mb-2">
        <CalendarDays className="h-4 w-4" />
        <span className="text-sm font-semibold tracking-tight">This Week</span>
      </div>
      <div className="space-y-2">
        {entries.map((e, i) => (
          <div key={i} className="flex items-center justify-between rounded-xl border border-black/10 dark:border-white/10 bg-white/70 dark:bg-white/5 px-3 py-2 text-sm">
            <div className="font-medium">{e.when}</div>
            <div className="text-gray-600 dark:text-gray-300">{e.count} orders • {e.total} ETB</div>
          </div>
        ))}
      </div>
    </div>
  );
}

