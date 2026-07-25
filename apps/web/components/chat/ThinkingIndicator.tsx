export default function ThinkingIndicator({
  label,
}: {
  label?: string | null;
}) {
  return (
    <div className="flex items-center gap-2 text-gray-400">
      <span className="flex gap-1">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400" />
      </span>
      <span className="animate-pulse text-sm italic">
        {label || "Thinking"}…
      </span>
    </div>
  );
}
