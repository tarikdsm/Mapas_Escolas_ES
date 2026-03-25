import { formatNumber } from "./utils.js";

function buildSwitch(layer) {
  const disabled = layer.status !== "ready" ? "disabled" : "";
  const checked = layer.defaultVisible ? "checked" : "";
  const stateClass = layer.status === "ready" ? "" : " layer-chip--disabled";
  const chipLabel = layer.status === "ready" ? "Disponível" : "Em preparação";

  return `
    <article class="layer-toggle" data-layer-id="${layer.id}">
      <div class="layer-toggle__meta">
        <div class="layer-toggle__title-row">
          <span class="layer-toggle__title">${layer.label}</span>
          <span class="layer-chip${stateClass}" style="--chip-color:${layer.color || "#0f3551"}">
            ${chipLabel}
          </span>
        </div>
        <div class="layer-toggle__description">${layer.description}</div>
      </div>
      <label class="switch" aria-label="${layer.label}">
        <input type="checkbox" data-toggle-id="${layer.id}" ${disabled} ${checked} />
        <span class="switch__track" style="--switch-color:${layer.color || "#0f3551"}"></span>
        <span class="switch__thumb"></span>
      </label>
    </article>
  `;
}

export function renderLayerControls(root, config) {
  const schoolMarkup = config.schoolLayers.map((layer) => buildSwitch(layer)).join("");
  const densityMarkup = buildSwitch({
    ...config.densityLayer,
    color: "#db6d30",
  });

  root.innerHTML = schoolMarkup + densityMarkup;
}

export function attachPanelToggle(button, sidebar) {
  button.addEventListener("click", () => {
    const next = !sidebar.classList.contains("is-open");
    sidebar.classList.toggle("is-open", next);
    button.setAttribute("aria-expanded", String(next));
  });
}

export function updateSummary({
  visibleSchoolCount,
  activeLayerCount,
  activeChips,
  details,
}) {
  document.getElementById("visible-school-count").textContent =
    formatNumber(visibleSchoolCount);
  document.getElementById("active-layer-count").textContent =
    formatNumber(activeLayerCount);
  document.getElementById("active-layer-chips").innerHTML = activeChips;
  document.getElementById("active-layer-details").innerHTML = details;
}

export function renderDensityLegend(layerInstance) {
  const legendRoot = document.getElementById("density-legend");
  const scaleRoot = document.getElementById("density-legend-scale");
  const captionRoot = document.getElementById("density-legend-caption");
  const legend = layerInstance?.metadata?.legend ?? [];

  if (!legend.length) {
    legendRoot.hidden = true;
    return;
  }

  scaleRoot.innerHTML = legend
    .map(
      (item) => `
        <div class="density-legend__item">
          <span class="density-legend__swatch" style="background:${item.color}"></span>
          <span>${item.label}</span>
        </div>
      `
    )
    .join("");

  captionRoot.textContent =
    layerInstance.metadata?.source_note ??
    "Densidade demográfica municipal oficial do IBGE.";
  legendRoot.hidden = false;
}

export function hideDensityLegend() {
  document.getElementById("density-legend").hidden = true;
}

export function setStatus(message) {
  document.getElementById("map-status").textContent = message;
}

