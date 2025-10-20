"use client";

import React from "react";

export default function ImageMessage({ url, caption }: { url: string; caption?: string }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-black/10 dark:border-white/10 bg-white/75 dark:bg-white/5 shadow-sm">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={url} alt={caption || "Generated image"} className="w-full h-auto block" />
      {caption ? (
        <div className="px-3 py-2 text-xs text-gray-600 dark:text-gray-300 border-t border-black/10 dark:border-white/10">
          {caption}
        </div>
      ) : null}
    </div>
  );
}

