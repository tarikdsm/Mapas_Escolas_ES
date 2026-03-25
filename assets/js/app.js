import { createDensityLayer, createSchoolLayer, createStateFrame } from "./map-layers.js";
import {
  attachPanelToggle,
  hideDensityLegend,
  renderDensityLegend,
  renderLayerControls,
  setStatus,
  updateSummary,
} from "./ui.js";
import { escapeHtml, formatNumber } from "./utils.js";

const CONFIG_PATH = "data/config/app-config.json";

function createMap(config) {
  const map = L.map("map", {
    zoomControl: false,
    minZoom: config.map.minZoom,
    maxZoom: config.map.maxZoom,
    maxBoundsViscosity: 1,
    preferCanvas: true,
  });

  map.createPane("stateMaskPane");
  map.getPane("stateMaskPane").style.zIndex = 350;

  map.createPane("densityPane");
  map.getPane("densityPane").style.zIndex = 410;

  map.createPane("stateOutlinePane");
  map.getPane("stateOutlinePane").style.zIndex = 500;

  L.tileLayer(config.map.tileLayer.url, {
    attribution: config.map.tileLayer.attribution,
    subdomains: config.map.tileLayer.subdomains,
    maxZoom: config.map.maxZoom,
    noWrap: true,
  }).addTo(map);

  L.control.zoom({ position: "topright" }).addTo(map);
  map.setView(config.map.center, config.map.zoom);

  return map;
}

function buildActiveChips(appState, config) {
  const chips = [];

  for (const layerId of appState.activeSchoolLayerIds) {
    const layerConfig = config.schoolLayers.find((item) => item.id === layerId);
    if (!layerConfig) {
      continue;
    }

    chips.push(
      `<span class="layer-chip" style="--chip-color:${layerConfig.color}">
        ${escapeHtml(layerConfig.label)}
      </span>`
    );
  }

  if (appState.densityActive) {
    chips.push(
      `<span class="layer-chip" style="--chip-color:#db6d30">
        ${escapeHtml(config.densityLayer.label)}
      </span>`
    );
  }

  if (!chips.length) {
    return `<span class="layer-chip layer-chip--disabled">Nenhuma camada ativa</span>`;
  }

  return chips.join("");
}

function buildActiveDetails(appState, config) {
  const lines = [];

  if (appState.activeSchoolLayerIds.size) {
    for (const layerId of appState.activeSchoolLayerIds) {
      const layerConfig = config.schoolLayers.find((item) => item.id === layerId);
      const instance = appState.loadedSchoolLayers.get(layerId);
      const count = instance?.featureCount ?? 0;
      lines.push(
        `<p><strong>${escapeHtml(layerConfig.label)}:</strong> ${formatNumber(count)} registros no mapa.</p>`
      );
    }
  }

  if (appState.densityActive && appState.densityLayer) {
    lines.push(
      `<p><strong>${escapeHtml(config.densityLayer.label)}:</strong> ${formatNumber(
        appState.densityLayer.featureCount
      )} municípios com densidade oficial do IBGE.</p>`
    );
  }

  if (!lines.length) {
    lines.push(
      "<p>Ative uma camada para visualizar escolas, clusters e a análise municipal.</p>"
    );
  }

  return lines.join("");
}

function refreshSummary(appState, config) {
  let visibleSchoolCount = 0;
  for (const layerId of appState.activeSchoolLayerIds) {
    visibleSchoolCount += appState.loadedSchoolLayers.get(layerId)?.featureCount ?? 0;
  }

  updateSummary({
    visibleSchoolCount,
    activeLayerCount:
      appState.activeSchoolLayerIds.size + (appState.densityActive ? 1 : 0),
    activeChips: buildActiveChips(appState, config),
    details: buildActiveDetails(appState, config),
  });
}

async function toggleSchoolLayer({
  map,
  appState,
  config,
  layerId,
  enabled,
  fitOnFirstLoad = false,
}) {
  const layerConfig = config.schoolLayers.find((item) => item.id === layerId);
  if (!layerConfig || layerConfig.status !== "ready") {
    return;
  }

  if (enabled) {
    let instance = appState.loadedSchoolLayers.get(layerId);
    if (!instance) {
      setStatus(`Carregando ${layerConfig.label.toLowerCase()}...`);
      instance = await createSchoolLayer(map, layerConfig);
      appState.loadedSchoolLayers.set(layerId, instance);
    }

    if (!map.hasLayer(instance.layer)) {
      instance.layer.addTo(map);
    }
    appState.activeSchoolLayerIds.add(layerId);

    if (fitOnFirstLoad && instance.bounds?.isValid()) {
      map.fitBounds(instance.bounds.pad(0.08));
    }
    setStatus(`${layerConfig.label} ativa.`);
  } else {
    const instance = appState.loadedSchoolLayers.get(layerId);
    if (instance && map.hasLayer(instance.layer)) {
      map.removeLayer(instance.layer);
    }
    appState.activeSchoolLayerIds.delete(layerId);
    setStatus(`${layerConfig.label} oculta.`);
  }

  refreshSummary(appState, config);
}

async function toggleDensityLayer({ map, appState, config, enabled }) {
  if (enabled) {
    if (!appState.densityLayer) {
      setStatus("Carregando densidade populacional...");
      appState.densityLayer = await createDensityLayer(map, config.densityLayer);
    }

    if (!map.hasLayer(appState.densityLayer.layer)) {
      appState.densityLayer.layer.addTo(map);
      appState.densityLayer.layer.bringToBack();
    }

    appState.densityActive = true;
    renderDensityLegend(appState.densityLayer);
    setStatus("Densidade populacional ativa.");
  } else {
    if (appState.densityLayer?.layer && map.hasLayer(appState.densityLayer.layer)) {
      map.removeLayer(appState.densityLayer.layer);
    }
    appState.densityActive = false;
    hideDensityLegend();
    setStatus("Densidade populacional oculta.");
  }

  refreshSummary(appState, config);
}

async function bootstrap() {
  const response = await fetch(CONFIG_PATH);
  if (!response.ok) {
    throw new Error("Não foi possível carregar a configuração do site.");
  }

  const config = await response.json();
  const map = createMap(config);
  const stateFrame = await createStateFrame(map, config.stateBoundary);
  if (stateFrame.maskLayer) {
    stateFrame.maskLayer.addTo(map);
  }
  stateFrame.outlineLayer.addTo(map);
  if (stateFrame.bounds?.isValid()) {
    map.setMaxBounds(stateFrame.bounds.pad(config.map.maxBoundsPadding ?? 0.14));
    map.fitBounds(stateFrame.bounds, {
      animate: false,
      padding: [config.map.fitPadding ?? 20, config.map.fitPadding ?? 20],
    });
  }

  const sidebar = document.getElementById("sidebar");
  const panelToggle = document.getElementById("panel-toggle");
  attachPanelToggle(panelToggle, sidebar);
  renderLayerControls(document.getElementById("layer-controls"), config);

  const appState = {
    loadedSchoolLayers: new Map(),
    activeSchoolLayerIds: new Set(),
    densityLayer: null,
    densityActive: false,
  };

  const toggles = Array.from(document.querySelectorAll("[data-toggle-id]"));
  for (const toggle of toggles) {
    toggle.addEventListener("change", async (event) => {
      const target = event.currentTarget;
      const layerId = target.dataset.toggleId;
      const schoolLayer = config.schoolLayers.find((item) => item.id === layerId);

      try {
        if (schoolLayer) {
          await toggleSchoolLayer({
            map,
            appState,
            config,
            layerId,
            enabled: target.checked,
          });
        } else if (layerId === config.densityLayer.id) {
          await toggleDensityLayer({
            map,
            appState,
            config,
            enabled: target.checked,
          });
        }
      } catch (error) {
        target.checked = false;
        setStatus(error.message);
      }
    });
  }

  refreshSummary(appState, config);

  for (const layerConfig of config.schoolLayers.filter(
    (item) => item.status === "ready" && item.defaultVisible
  )) {
    await toggleSchoolLayer({
      map,
      appState,
      config,
      layerId: layerConfig.id,
      enabled: true,
      fitOnFirstLoad: false,
    });
  }

  if (config.densityLayer.defaultVisible) {
    await toggleDensityLayer({
      map,
      appState,
      config,
      enabled: true,
    });
  }

  setStatus("Mapa pronto.");
}

bootstrap().catch((error) => {
  console.error(error);
  setStatus("Falha ao iniciar o mapa.");
});
