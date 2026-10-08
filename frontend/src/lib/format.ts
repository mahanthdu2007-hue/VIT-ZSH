const indianNumber = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

/** 500000 → "5,00,000" (Indian digit grouping). */
export function formatIndian(value: number): string {
  return indianNumber.format(value);
}

/** 500000 → "₹5,00,000". */
export function formatInr(value: number): string {
  return `₹${formatIndian(value)}`;
}

/** 500000 → "5 lakh", 12500000 → "1.25 crore"; for helper text under money inputs. */
export function inrInWords(value: number): string {
  const trim = (n: number) => String(Number(n.toFixed(2)));
  if (value >= 1_00_00_000) return `${trim(value / 1_00_00_000)} crore`;
  if (value >= 1_00_000) return `${trim(value / 1_00_000)} lakh`;
  if (value >= 1_000) return `${trim(value / 1_000)} thousand`;
  return formatIndian(value);
}

/** Keeps only the digits a person typed: "5,00,000" → 500000; empty → null. */
export function parseIndian(text: string): number | null {
  const digits = text.replace(/\D/g, "");
  return digits === "" ? null : Number(digits);
}

/** One decimal place, as the engine reports points. */
export function formatPoints(value: number): string {
  return value.toFixed(1);
}

/** A 0–1 utility shown on a 0–100 scale with a sign: 0.121 → "+12.1". */
export function formatSignedHundredths(value: number): string {
  const scaled = Math.round(value * 1000) / 10;
  return `${scaled > 0 ? "+" : scaled < 0 ? "−" : ""}${Math.abs(scaled).toFixed(1)}`;
}

export function wordCount(text: string): number {
  return text.trim() === "" ? 0 : text.trim().split(/\s+/).length;
}
