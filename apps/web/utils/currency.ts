// Report costs are stored in USD (the model is priced in USD). We display
// rupees first with the dollar figure in brackets. The FX rate is an
// approximate, configurable constant — these are illustrative micro-costs, not
// billing — override via NEXT_PUBLIC_USD_TO_INR.
export const USD_TO_INR = Number(process.env.NEXT_PUBLIC_USD_TO_INR ?? 88);

export function formatUsd(usd: number): string {
  if (usd === 0) return "$0.00";
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(usd < 1 ? 3 : 2)}`;
}

export function formatInr(usd: number): string {
  const inr = usd * USD_TO_INR;
  if (inr === 0) return "₹0.00";
  if (inr >= 100) return `₹${Math.round(inr).toLocaleString("en-IN")}`;
  return `₹${inr.toFixed(2)}`;
}

/** Rupees first, dollars in brackets — e.g. "₹0.22 ($0.0025)". */
export function formatCostDual(usd: number): string {
  return `${formatInr(usd)} (${formatUsd(usd)})`;
}
