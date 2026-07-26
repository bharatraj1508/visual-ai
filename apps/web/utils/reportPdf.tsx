"use client";

import { createRoot } from "react-dom/client";

import ChartRenderer from "@/components/chart/ChartRenderer";
import { colorAt } from "@/components/chart/palette";
import { ChartSpec } from "@/types/chart";
import { ReportDetail, ReportSection } from "@/types/report";

const PRINT_WIDTH = 680;
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

/** Light markdown → plain text so jsPDF renders readable prose. */
function stripMd(md: string): string {
  return md
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/\*(.*?)\*/g, "$1")
    .replace(/`(.*?)`/g, "$1")
    .replace(/^#+\s*/gm, "")
    .replace(/^\s*[-*]\s+/gm, "• ")
    .trim();
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  const n = parseInt(
    h.length === 3
      ? h
          .split("")
          .map((c) => c + c)
          .join("")
      : h,
    16,
  );
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/** Render a Recharts SVG node to a white-background PNG data URL. Reliable —
 * unlike whole-DOM capture, an SVG serialized to an <img> rasterizes cleanly. */
async function svgToPng(svg: SVGSVGElement): Promise<string | null> {
  const rect = svg.getBoundingClientRect();
  const w = svg.width?.baseVal?.value || rect.width || PRINT_WIDTH;
  const h = svg.height?.baseVal?.value || rect.height || 320;
  const clone = svg.cloneNode(true) as SVGSVGElement;
  clone.setAttribute("width", String(w));
  clone.setAttribute("height", String(h));
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  // Default font so axis/labels aren't a serif fallback in the standalone SVG.
  clone.style.fontFamily = "Arial, Helvetica, sans-serif";
  const xml = new XMLSerializer().serializeToString(clone);
  const url = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(xml);

  const img = new Image();
  const ok = await new Promise<boolean>((resolve) => {
    img.onload = () => resolve(true);
    img.onerror = () => resolve(false);
    img.src = url;
  });
  if (!ok) return null;

  const scale = 2;
  const canvas = document.createElement("canvas");
  canvas.width = w * scale;
  canvas.height = h * scale;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  ctx.scale(scale, scale);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);
  ctx.drawImage(img, 0, 0, w, h);
  return canvas.toDataURL("image/png");
}

/** Render every chart off-screen, wait for Recharts to paint, return the PNGs
 * in order (one per chart spec). */
async function renderChartPngs(charts: ChartSpec[]): Promise<(string | null)[]> {
  if (charts.length === 0) return [];
  const host = document.createElement("div");
  host.style.cssText = `position:fixed;top:0;left:-10000px;width:${PRINT_WIDTH}px;background:#fff;`;
  document.body.appendChild(host);
  const root = createRoot(host);
  try {
    root.render(
      <div>
        {charts.map((spec, i) => (
          <div key={i} style={{ width: PRINT_WIDTH }}>
            <ChartRenderer spec={spec} print />
          </div>
        ))}
      </div>,
    );
    // Poll until Recharts has committed all surfaces (or time out).
    for (let i = 0; i < 40; i++) {
      await delay(50);
      if (host.querySelectorAll("svg.recharts-surface").length >= charts.length)
        break;
    }
    await delay(100);
    const svgs = Array.from(
      host.querySelectorAll<SVGSVGElement>("svg.recharts-surface"),
    );
    return Promise.all(svgs.map((s) => svgToPng(s)));
  } finally {
    root.unmount();
    host.remove();
  }
}

/** Build a clean, text-based PDF with embedded chart images. */
export async function reportToPdfBlob(report: ReportDetail): Promise<Blob> {
  const { jsPDF } = await import("jspdf");
  const sections: ReportSection[] = report.content ?? [];
  const chartPngs = await renderChartPngs(sections.flatMap((s) => s.charts ?? []));

  const pdf = new jsPDF({ unit: "pt", format: "a4" });
  const pageW = pdf.internal.pageSize.getWidth();
  const pageH = pdf.internal.pageSize.getHeight();
  const margin = 42;
  const maxW = pageW - margin * 2;
  let y = margin;

  const ensure = (h: number) => {
    if (y + h > pageH - margin) {
      pdf.addPage();
      y = margin;
    }
  };
  const writeText = (
    text: string,
    size: number,
    style: "normal" | "bold",
    rgb: [number, number, number],
    gap = 1.42,
  ) => {
    pdf.setFont("helvetica", style);
    pdf.setFontSize(size);
    pdf.setTextColor(...rgb);
    for (const line of pdf.splitTextToSize(text, maxW)) {
      ensure(size * gap);
      pdf.text(line, margin, y);
      y += size * gap;
    }
  };

  // Header
  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(9);
  pdf.setTextColor(251, 103, 110);
  pdf.text("VISUAL AI", margin, y);
  y += 16;
  writeText(report.title, 20, "bold", [17, 24, 39]);
  y += 4;
  writeText(report.goal, 10, "normal", [107, 114, 128]);
  y += 14;

  let ci = 0;
  for (const section of sections) {
    ensure(26);
    writeText(section.title, 14, "bold", [17, 24, 39]);
    y += 3;
    if (section.narrative) {
      writeText(stripMd(section.narrative), 10.5, "normal", [55, 65, 81]);
      y += 6;
    }
    for (const spec of section.charts ?? []) {
      const png = chartPngs[ci++];
      if (!png) continue;
      const img = new Image();
      img.src = png;
      // eslint-disable-next-line no-await-in-loop
      await img.decode().catch(() => undefined);
      const w = maxW;
      const h = img.width ? (img.height / img.width) * w : 240;
      ensure(h + 10);
      pdf.addImage(png, "PNG", margin, y, w, h);
      y += h + 6;
      // Text legend for multi-series charts (Recharts' HTML legend isn't in the SVG).
      const names = (spec.series ?? []).map((s) => s.name).filter(Boolean);
      if (names.length > 1) {
        ensure(14);
        let x = margin;
        names.forEach((name, i) => {
          const [r, g, b] = hexToRgb(colorAt(i));
          pdf.setFillColor(r, g, b);
          pdf.rect(x, y - 7, 8, 8, "F");
          pdf.setFont("helvetica", "normal");
          pdf.setFontSize(9);
          pdf.setTextColor(75, 85, 99);
          pdf.text(name, x + 11, y);
          x += 11 + pdf.getTextWidth(name) + 14;
        });
        y += 12;
      }
      y += 10;
    }
    y += 8;
  }
  return pdf.output("blob");
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

export async function downloadReportPdf(report: ReportDetail): Promise<void> {
  const blob = await reportToPdfBlob(report);
  triggerDownload(blob, `${safeName(report.title)}.pdf`);
}

export async function downloadReportsZip(
  reports: ReportDetail[],
  zipName: string,
): Promise<void> {
  const JSZip = (await import("jszip")).default;
  const zip = new JSZip();
  const seen = new Map<string, number>();
  for (const report of reports) {
    // eslint-disable-next-line no-await-in-loop
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
