export function formatNumber(value, options = {}) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "0";
  }

  return new Intl.NumberFormat("pt-BR", options).format(Number(value));
}

export function formatDensity(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "n/d";
  }

  return `${formatNumber(value, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} hab/km²`;
}

export function formatCoordinates(lat, lng) {
  if (
    lat === null ||
    lat === undefined ||
    lng === null ||
    lng === undefined ||
    Number.isNaN(Number(lat)) ||
    Number.isNaN(Number(lng))
  ) {
    return "n/d";
  }

  return `${Number(lat).toFixed(5)}, ${Number(lng).toFixed(5)}`;
}

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

