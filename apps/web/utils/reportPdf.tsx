"use client";

import { createRoot } from "react-dom/client";

import ChartRenderer from "@/components/chart/ChartRenderer";
import MarkdownMessage from "@/components/chat/MarkdownMessage";
import { ReportDetail, ReportSection } from "@/types/report";

const PAGE_WIDTH = 794; // ~A4 width in px @ 96dpi

const raf = () => new Promise((r) => requestAnimationFrame(() => r(null)));
const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

function safeName(title: string): string {
  return (
    (title || "report")
      .replace(/[^\w\s-]/g, "")
      .trim()
      .replace(/\s+/g, "-")
      .slice(0, 80) || "report"
  );
}

/** Off-screen printable version of a report (charts static, no animation). */
function ReportPrintable({ report }: { report: ReportDetail }) {
  const sections: ReportSection[] = report.content ?? [];
  return (
    <div style={{ color: "#111827", fontFamily: "system-ui, sans-serif" }}>
      <div
        style={{
          borderBottom: "1px solid #E5E7EB",
          paddingBottom: 16,
          marginBottom: 24,
        }}
      >
        <div style={{ fontSize: 12, fontWeight: 700, color: "#FB676E" }}>
          Visual AI
        </div>
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: "8px 0 6px" }}>
          {report.title}
        </h1>
        <p style={{ fontSize: 12, lineHeight: 1.5, color: "#6B7280" }}>
          {report.goal}
        </p>
      </div>
      {sections.map((s, i) => (
        <div key={i} style={{ marginBottom: 28 }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>
            {s.title}
          </h2>
          {s.narrative && (
            <div className="prose prose-sm max-w-none">
              <MarkdownMessage content={s.narrative} />
            </div>
          )}
          {(s.charts ?? []).map((spec, ci) => (
            <div key={ci} style={{ marginTop: 12 }}>
              <ChartRenderer spec={spec} print />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

/** Render a report off-screen and rasterize it into a PDF blob. */
export async function reportToPdfBlob(report: ReportDetail): Promise<Blob> {
  const host = document.createElement("div");
  host.style.cssText = `position:fixed;top:0;left:-10000px;width:${PAGE_WIDTH}px;background:#fff;padding:32px;box-sizing:border-box;z-index:-1;`;
  document.body.appendChild(host);
  const root = createRoot(host);
  try {
    // Lazy-load the browser-only PDF libs so they never run during SSR/build.
    const [{ toPng }, { jsPDF }] = await Promise.all([
      import("html-to-image"),
      import("jspdf"),
    ]);

    root.render(<ReportPrintable report={report} />);
    // Let React commit and Recharts paint its (static) SVG.
    await raf();
    await raf();
    await delay(500);

    const dataUrl = await toPng(host, {
      pixelRatio: 2,
      backgroundColor: "#ffffff",
      width: host.offsetWidth,
      height: host.offsetHeight,
    });

    const img = new Image();
    img.src = dataUrl;
    await img.decode();

    const pdf = new jsPDF({ unit: "pt", format: "a4" });
    const pageW = pdf.internal.pageSize.getWidth();
    const pageH = pdf.internal.pageSize.getHeight();
    const imgH = (img.height / img.width) * pageW;

    if (imgH <= pageH) {
      pdf.addImage(dataUrl, "PNG", 0, 0, pageW, imgH);
    } else {
      // Slice a tall image across pages via negative y-offset.
      let position = 0;
      let remaining = imgH;
      while (remaining > 0) {
        pdf.addImage(dataUrl, "PNG", 0, position, pageW, imgH);
        remaining -= pageH;
        if (remaining > 0) {
          pdf.addPage();
          position -= pageH;
        }
      }
    }
    return pdf.output("blob");
  } finally {
    root.unmount();
    host.remove();
  }
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Download a single report as a PDF. */
export async function downloadReportPdf(report: ReportDetail): Promise<void> {
  const blob = await reportToPdfBlob(report);
  triggerDownload(blob, `${safeName(report.title)}.pdf`);
}

/** Zip every report version's PDF and download it. */
export async function downloadReportsZip(
  reports: ReportDetail[],
  zipName: string,
): Promise<void> {
  const JSZip = (await import("jszip")).default;
  const zip = new JSZip();
  const seen = new Map<string, number>();
  for (const report of reports) {
    const blob = await reportToPdfBlob(report);
    let base = safeName(report.title);
    const n = seen.get(base) ?? 0;
    seen.set(base, n + 1);
    if (n > 0) base = `${base}-v${n + 1}`;
    zip.file(`${base}.pdf`, blob);
  }
  const out = await zip.generateAsync({ type: "blob" });
  triggerDownload(out, `${safeName(zipName)}.zip`);
}
