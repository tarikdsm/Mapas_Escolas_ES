import { escapeHtml, formatCoordinates, formatDensity, formatNumber } from "./utils.js";

const LAYER_SYMBOLS = {
  municipais: `
    <path fill="#ffffff" d="M24 13 13 18v2h2.6V31H13v3h22v-3h-2.6V20H35v-2L24 13Zm-6 7.2h2.3V31H18V20.2Zm4.9 0h2.3V31h-2.3V20.2Zm4.9 0H30V31h-2.2V20.2Z"/>
  `,
  estaduais: `
    <path fill="#ffffff" d="M14 18.7 24 13l10 5.7V30c0 .6-.4 1-1 1h-3v-7.2h-4V31h-4v-7.2h-4V31h-3c-.6 0-1-.4-1-1V18.7Zm9.2-.4h1.6v1.5h-1.6v-1.5Z"/>
  `,
  federais: `
    <path fill="#ffffff" d="M24 13.2 27.1 19.6l7 .9-5 4.8 1.2 6.9L24 28.8l-6.3 3.4 1.2-6.9-5-4.8 7-.9L24 13.2Z"/>
  `,
  particulares: `
    <path fill="#ffffff" d="M16 15.6c2.6 0 4.6.7 6 1.9 1.4-1.2 3.4-1.9 6-1.9 2 0 3.8.3 5.5 1V30c-1.6-.7-3.4-1-5.5-1-2.7 0-4.4.8-6 2.1-1.6-1.3-3.3-2.1-6-2.1-2.1 0-3.9.3-5.5 1V16.6c1.6-.7 3.4-1 5.5-1Zm5.1 3.8c-.9-.7-2.1-1.1-3.9-1.1-1.1 0-2.1.1-3.1.5v7.2c1-.4 2-.5 3.1-.5 1.8 0 3 .4 3.9 1.1v-7.2Zm1.8 7.2c.9-.7 2.1-1.1 3.9-1.1 1.1 0 2.1.1 3.1.5v-7.2c-1-.4-2-.5-3.1-.5-1.8 0-3 .4-3.9 1.1v7.2Z"/>
  `,
};

const MARKER_TEMPLATE = `
  <svg viewBox="0 0 48 48" aria-hidden="true">
    <path fill="COLOR" d="M24 2c-8.3 0-15 6.7-15 15 0 10.4 12.1 25.2 14 27.4.5.6 1.5.6 2 0C26.9 42.2 39 27.4 39 17c0-8.3-6.7-15-15-15Z"/>
    SYMBOL
  </svg>
`;

function buildSchoolMarkerIcon(layerConfig) {
  const symbol = LAYER_SYMBOLS[layerConfig.id] || LAYER_SYMBOLS.estaduais;
  return L.divIcon({
    className: "school-marker",
    html: MARKER_TEMPLATE.replace("COLOR", layerConfig.color).replace("SYMBOL", symbol),
    iconSize: [28, 28],
    iconAnchor: [14, 28],
    popupAnchor: [0, -24],
  });
}

function buildClusterIcon(color, count) {
  return L.divIcon({
    className: "",
    html: `<div class="school-cluster" style="--cluster-color:${color}"><span>${count}</span></div>`,
    iconSize: [38, 38],
  });
}

function coordinatesToLatLngs(ring) {
  return ring.map(([longitude, latitude]) => [latitude, longitude]);
}

function extractStateHoles(geometry) {
  if (!geometry) {
    return [];
  }

  if (geometry.type === "Polygon") {
    return [coordinatesToLatLngs(geometry.coordinates[0])];
  }

  if (geometry.type === "MultiPolygon") {
    return geometry.coordinates.map((polygon) => coordinatesToLatLngs(polygon[0]));
  }

  return [];
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
  const icon = buildSchoolMarkerIcon(layerConfig);
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

export async function createStateFrame(map, stateConfig) {
  const response = await fetch(stateConfig.dataPath);
  if (!response.ok) {
    throw new Error(`Falha ao carregar ${stateConfig.dataPath}`);
  }

  const geojson = await response.json();
  const feature = geojson.features?.[0];
  const outlineLayer = L.geoJSON(geojson, {
    pane: "stateOutlinePane",
    interactive: false,
    style: {
      color: stateConfig.borderColor,
      weight: stateConfig.borderWeight,
      opacity: 1,
      fill: false,
      lineJoin: "round",
    },
  });

  const maskHoles = extractStateHoles(feature?.geometry);
  const maskLayer =
    maskHoles.length > 0
      ? L.polygon(
          [
            [
              [89, -360],
              [89, 360],
              [-89, 360],
              [-89, -360],
            ],
            ...maskHoles,
          ],
          {
            pane: "stateMaskPane",
            stroke: false,
            fillColor: stateConfig.maskColor,
            fillOpacity: stateConfig.maskOpacity,
            interactive: false,
          }
        )
      : null;

  return {
    source: geojson,
    outlineLayer,
    maskLayer,
    bounds: outlineLayer.getBounds(),
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
