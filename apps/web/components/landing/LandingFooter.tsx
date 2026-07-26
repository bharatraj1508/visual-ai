import Link from "next/link";

const COLUMNS = [
  {
    heading: "Product",
    links: [
      { label: "Get started", href: "/auth/register" },
      { label: "Log in", href: "/auth/login" },
      { label: "Dashboard", href: "/dashboard" },
    ],
  },
  {
    heading: "Explore",
    links: [
      { label: "How it works", href: "#how" },
      { label: "Reports", href: "#showcase" },
      { label: "Charts", href: "#charts" },
    ],
  },
];

export default function LandingFooter() {
  return (
    <footer className="relative overflow-hidden border-t border-gray-200 bg-gradient-to-b from-white to-gray-50">
      {/* coral hairline accent */}
      <div
        aria-hidden
        className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent"
      />

      <div className="relative mx-auto max-w-6xl px-5 pt-16 sm:px-8">
        <div className="grid gap-12 md:grid-cols-[1.6fr_1fr_1fr]">
          {/* brand */}
          <div>
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-primary" />
              <span className="font-display text-lg font-semibold tracking-tight text-ink">
                Visual&nbsp;AI
              </span>
            </div>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-gray-500">
              The AI data analyst that reads your CSV and writes the report —
              findings, narrative, and interactive charts.
            </p>
            <p className="mt-4 font-mono text-xs text-gray-400">
              csv in → report out. no chat window.
            </p>
          </div>

          {COLUMNS.map((col) => (
            <div key={col.heading}>
              <h3 className="font-mono text-xs uppercase tracking-wider text-gray-400">
                {col.heading}
              </h3>
              <ul className="mt-4 space-y-3">
                {col.links.map((l) => (
                  <li key={l.label}>
                    <Link
                      href={l.href}
                      className="text-sm text-gray-500 transition-colors hover:text-primary"
                    >
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* developer credit */}
        <div className="mt-14 flex flex-col gap-5 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-[#ff8a80] font-display text-lg font-semibold text-white shadow-lg shadow-primary/25">
              BV
            </div>
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-gray-400">
                designed &amp; built by
              </p>
              <p className="font-display text-base font-semibold text-ink">
                Bharat Raj Verma
              </p>
              <p className="text-sm text-gray-500">Sr. Full Stack Developer</p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <a
              href="https://github.com/bharatraj1508"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="GitHub"
              className="rounded-xl border border-gray-200 p-2.5 text-gray-500 transition-colors hover:border-primary/40 hover:text-primary"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 .5A11.5 11.5 0 0 0 .5 12a11.5 11.5 0 0 0 7.86 10.92c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.53-1.34-1.29-1.7-1.29-1.7-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.2 1.77 1.2 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.72-1.55-2.55-.29-5.24-1.28-5.24-5.68 0-1.26.45-2.28 1.19-3.08-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11 11 0 0 1 5.79 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.24 2.76.12 3.05.74.8 1.19 1.82 1.19 3.08 0 4.41-2.69 5.38-5.25 5.67.41.36.78 1.05.78 2.12v3.14c0 .31.21.67.8.56A11.5 11.5 0 0 0 23.5 12 11.5 11.5 0 0 0 12 .5Z" />
              </svg>
            </a>
            <a
              href="https://www.linkedin.com/in/bharatraj1508"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="LinkedIn"
              className="rounded-xl border border-gray-200 p-2.5 text-gray-500 transition-colors hover:border-primary/40 hover:text-primary"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5ZM3 9h4v12H3V9Zm7 0h3.8v1.64h.05c.53-1 1.83-2.05 3.77-2.05 4.03 0 4.78 2.65 4.78 6.1V21h-4v-5.4c0-1.29-.02-2.94-1.79-2.94-1.8 0-2.07 1.4-2.07 2.85V21h-4V9Z" />
              </svg>
            </a>
          </div>
        </div>

        <div className="mt-10 flex flex-col items-start justify-between gap-3 border-t border-gray-200 py-6 sm:flex-row sm:items-center">
          <p className="text-xs text-gray-400">
            © {new Date().getFullYear()} Visual AI. Crafted by Bharat Raj Verma.
          </p>
          <p className="font-mono text-[11px] text-gray-400">
            FastAPI · Next.js · Gemini · DuckDB · Recharts
          </p>
        </div>
      </div>

      {/* oversized wordmark signature, half-clipped at the base */}
      <div
        aria-hidden
        className="pointer-events-none relative mx-auto max-w-6xl select-none px-5 sm:px-8"
      >
        <span className="block translate-y-[18%] bg-gradient-to-b from-gray-200 to-transparent bg-clip-text font-display text-[19vw] font-bold leading-none tracking-tighter text-transparent">
          Visual&nbsp;AI
        </span>
      </div>
    </footer>
  );
}
