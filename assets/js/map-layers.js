import { escapeHtml, formatCoordinates, formatDensity, formatNumber } from "./utils.js";

const MARKER_SHAPE = `
  <svg viewBox="0 0 48 48" aria-hidden="true">
    <path fill="COLOR" d="M24 2c-8.3 0-15 6.7-15 15 0 10.4 12.1 25.2 14 27.4.5.6 1.5.6 2 0C26.9 42.2 39 27.4 39 17c0-8.3-6.7-15-15-15Z"/>
    <path fill="#ffffff" d="M14 18.7 24 13l10 5.7V30c0 .6-.4 1-1 1h-3v-7.2h-4V31h-4v-7.2h-4V31h-3c-.6 0-1-.4-1-1V18.7Zm9.2-.4h1.6v1.5h-1.6v-1.5Z"/>
  </svg>
`;

function buildSchoolMarkerIcon(color) {
  return L.divIcon({
    className: "school-marker",
    html: MARKER_SHAPE.replace("COLOR", color),
    iconSize: [34, 34],
    iconAnchor: [17, 34],
    popupAnchor: [0, -28],
  });
}

function buildClusterIcon(color, count) {
  return L.divIcon({
    className: "",
    html: `<div class="school-cluster" style="--cluster-color:${color}">${count}</div>`,
    iconSize: [44, 44],
  });
}

function buildAddress(properties) {
  const parts = [
    [properties.address, properties.number].filter(Boolean).join(", "),
    properties.district,
    properties.municipio,
    properties.uf,
    properties.postal_code,
  ].filter(Boolean);

  return parts.join(" · ");
}

function buildPopupMarkup(properties, layerConfig) {
  const statusClass =
    properties.status && properties.status.toLowerCase() === "em atividade"
      ? ""
      : " is-inactive";

  return `
    <article class="school-popup">
      <header class="school-popup__heading">
        <h3>${escapeHtml(properties.name)}</h3>
        <div class="school-popup__badges">
          <span class="popup-badge">${escapeHtml(layerConfig.label)}</span>
          <span class="popup-badge popup-badge--status${statusClass}">
            ${escapeHtml(properties.status || "Sem status")}
          </span>
        </div>
      </header>
      <div class="school-popup__grid">
        <div class="school-popup__row">
          <span class="school-popup__label">Município</span>
          <span class="school-popup__value">${escapeHtml(properties.municipio || "n/d")}</span>
        </div>
        <div class="school-popup__row">
          <span class="school-popup__label">Endereço</span>
          <span class="school-popup__value">${escapeHtml(buildAddress(properties) || "n/d")}</span>
        </div>
        <div class="school-popup__row">
          <span class="school-popup__label">Georreferenciamento</span>
          <span class="school-popup__value">
            ${escapeHtml(properties.classification || "n/d")} ·
            ${escapeHtml(properties.georef_source || "n/d")}
          </span>
        </div>
        <div class="school-popup__row">
          <span class="school-popup__label">Coordenadas</span>
          <span class="school-popup__value">${escapeHtml(
            formatCoordinates(properties.latitude, properties.longitude)
          )}</span>
        </div>
        <div class="school-popup__row">
          <span class="school-popup__label">Contato</span>
          <span class="school-popup__value">
            ${escapeHtml(properties.phone_primary || properties.email || "n/d")}
          </span>
        </div>
      </div>
    </article>
  `;
}

export async function createSchoolLayer(map, layerConfig) {
  const response = await fetch(layerConfig.dataPath);
  if (!response.ok) {
    throw new Error(`Falha ao carregar ${layerConfig.dataPath}`);
  }

  const geojson = await response.json();
  const icon = buildSchoolMarkerIcon(layerConfig.color);
  const features = Array.isArray(geojson.features) ? geojson.features : [];

  const clusterGroup = L.markerClusterGroup({
    showCoverageOnHover: false,
    spiderfyOnMaxZoom: true,
    maxClusterRadius: 48,
    iconCreateFunction(cluster) {
      return buildClusterIcon(layerConfig.color, cluster.getChildCount());
    },
  });

  const featureLayer = L.geoJSON(geojson, {
    pointToLayer(feature, latlng) {
      return L.marker(latlng, { icon, keyboard: true });
    },
    onEachFeature(feature, marker) {
      const properties = feature.properties ?? {};
      marker.bindPopup(buildPopupMarkup(properties, layerConfig), {
        maxWidth: 320,
      });
      marker.bindTooltip(escapeHtml(properties.name || layerConfig.label), {
        direction: "top",
        offset: [0, -20],
      });
    },
  });

  clusterGroup.addLayer(featureLayer);

  return {
    id: layerConfig.id,
    label: layerConfig.label,
    source: geojson,
    layer: clusterGroup,
    featureCount: features.length,
    bounds: featureLayer.getBounds(),
  };
}

function styleDensityFeature(feature, metadata) {
  const classes = metadata?.legend ?? [];
  const index = Number(feature.properties?.density_class ?? 0);
  const bucket = classes[Math.max(0, Math.min(index, classes.length - 1))];
  const fillColor = bucket?.color ?? "#d9d9d9";

  return {
    pane: "densityPane",
    color: "rgba(18, 53, 77, 0.24)",
    weight: 1,
    fillColor,
    fillOpacity: 0.72,
  };
}

function buildDensityPopup(feature) {
  const properties = feature.properties ?? {};
  return `
    <article class="school-popup">
      <header class="school-popup__heading">
        <h3>${escapeHtml(properties.municipio_nome || "Município")}</h3>
        <div class="school-popup__badges">
          <span class="popup-badge">Densidade populacional</span>
        </div>
      </header>
      <div class="school-popup__grid">
        <div class="school-popup__row">
          <span class="school-popup__label">Densidade</span>
          <span class="school-popup__value">${escapeHtml(
            formatDensity(properties.densidade_demografica)
          )}</span>
        </div>
        <div class="school-popup__row">
          <span class="school-popup__label">População no Censo 2022</span>
          <span class="school-popup__value">${escapeHtml(
            `${formatNumber(properties.populacao_censo_2022)} pessoas`
          )}</span>
        </div>
        <div class="school-popup__row">
          <span class="school-popup__label">Área Territorial</span>
          <span class="school-popup__value">${escapeHtml(
            `${formatNumber(properties.area_territorial_km2, {
              minimumFractionDigits: 3,
              maximumFractionDigits: 3,
            })} km²`
          )}</span>
        </div>
      </div>
    </article>
  `;
}

export async function createDensityLayer(map, densityConfig) {
  const response = await fetch(densityConfig.dataPath);
  if (!response.ok) {
    throw new Error(`Falha ao carregar ${densityConfig.dataPath}`);
  }

  const geojson = await response.json();
  const metadata = geojson.metadata ?? {};

  const layer = L.geoJSON(geojson, {
    style: (feature) => styleDensityFeature(feature, metadata),
    onEachFeature(feature, subLayer) {
      const originalStyle = styleDensityFeature(feature, metadata);

      subLayer.bindPopup(buildDensityPopup(feature), { maxWidth: 320 });
      subLayer.bindTooltip(
        `${feature.properties?.municipio_nome ?? "Município"} · ${formatDensity(
          feature.properties?.densidade_demografica
        )}`,
        { sticky: true, className: "density-tooltip" }
      );

      subLayer.on("mouseover", () => {
        subLayer.setStyle({
          ...originalStyle,
          weight: 2,
          fillOpacity: 0.9,
          color: "rgba(18, 53, 77, 0.45)",
        });
      });

      subLayer.on("mouseout", () => {
        subLayer.setStyle(originalStyle);
      });
    },
  });

  return {
    id: densityConfig.id,
    label: densityConfig.label,
    source: geojson,
    metadata,
    layer,
    featureCount: Array.isArray(geojson.features) ? geojson.features.length : 0,
    bounds: layer.getBounds(),
  };
}

