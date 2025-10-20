"use client";

import React, { useMemo } from "react";
import { markdownToHtml } from "@/lib/markdown";

export default function MarkdownContent({ text }: { text: string }) {
  const html = useMemo(() => markdownToHtml(text), [text]);
  return (
    <div
      className="prose prose-sm dark:prose-invert max-w-none mdx-content"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

