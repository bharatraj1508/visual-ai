"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders assistant content as Markdown (GFM: tables, lists, code, etc.).
 * Styled with @tailwindcss/typography; tables scroll horizontally.
 */
export default function MarkdownMessage({ content }: { content: string }) {
  return (
    <div className="prose prose-sm max-w-none overflow-x-auto break-words prose-pre:bg-gray-100 prose-pre:text-gray-800">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
