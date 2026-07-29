import Link from "next/link";

export interface Crumb {
  label: string;
  href?: string;
}

/** Compact breadcrumb trail. The last crumb renders as the current page. */
export default function Breadcrumb({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb" className="mb-4">
      <ol className="flex flex-wrap items-center gap-1.5 text-sm text-gray-500">
        {items.map((item, i) => {
          const last = i === items.length - 1;
          return (
            <li key={i} className="flex min-w-0 items-center gap-1.5">
              {item.href && !last ? (
                <Link
                  href={item.href}
                  className="max-w-[10rem] truncate transition-colors hover:text-primary sm:max-w-xs"
                >
                  {item.label}
                </Link>
              ) : (
                <span
                  className={`max-w-[10rem] truncate sm:max-w-xs ${
                    last ? "font-medium text-gray-900" : ""
                  }`}
                  aria-current={last ? "page" : undefined}
                >
                  {item.label}
                </span>
              )}
              {!last && <span className="text-gray-300">/</span>}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
