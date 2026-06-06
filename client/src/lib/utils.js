import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function formatDate(date) {
  return new Date(date).toLocaleDateString();
}

export function truncate(
  text,
  length = 60
) {
  if (!text) return "";

  return text.length > length
    ? text.substring(
        0,
        length
      ) + "..."
    : text;
}

export function formatNumber(
  value
) {
  return Intl.NumberFormat().format(
    value
  );
}