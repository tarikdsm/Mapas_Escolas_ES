(function () {
  "use strict";

  var CONFIG_PATH = "data/config/app-config.json";
  var LAYER_SYMBOLS = {
    municipais:
      '<path fill="#ffffff" d="M24 13 13 18v2h2.6V31H13v3h22v-3h-2.6V20H35v-2L24 13Zm-6 7.2h2.3V31H18V20.2Zm4.9 0h2.3V31h-2.3V20.2Zm4.9 0H30V31h-2.2V20.2Z"/>',
    estaduais:
      '<path fill="#ffffff" d="M14 18.7 24 13l10 5.7V30c0 .6-.4 1-1 1h-3v-7.2h-4V31h-4v-7.2h-4V31h-3c-.6 0-1-.4-1-1V18.7Zm9.2-.4h1.6v1.5h-1.6v-1.5Z"/>',
    federais:
      '<path fill="#ffffff" d="M24 13.2 27.1 19.6l7 .9-5 4.8 1.2 6.9L24 28.8l-6.3 3.4 1.2-6.9-5-4.8 7-.9L24 13.2Z"/>',
    particulares:
      '<path fill="#ffffff" d="M16 15.6c2.6 0 4.6.7 6 1.9 1.4-1.2 3.4-1.9 6-1.9 2 0 3.8.3 5.5 1V30c-1.6-.7-3.4-1-5.5-1-2.7 0-4.4.8-6 2.1-1.6-1.3-3.3-2.1-6-2.1-2.1 0-3.9.3-5.5 1V16.6c1.6-.7 3.4-1 5.5-1Zm5.1 3.8c-.9-.7-2.1-1.1-3.9-1.1-1.1 0-2.1.1-3.1.5v7.2c1-.4 2-.5 3.1-.5 1.8 0 3 .4 3.9 1.1v-7.2Zm1.8 7.2c.9-.7 2.1-1.1 3.9-1.1 1.1 0 2.1.1 3.1.5v-7.2c-1-.4-2-.5-3.1-.5-1.8 0-3 .4-3.9 1.1v7.2Z"/>',
  };
  var MARKER_TEMPLATE =
    '<svg viewBox="0 0 48 48" aria-hidden="true"><path fill="COLOR" d="M24 2c-8.3 0-15 6.7-15 15 0 10.4 12.1 25.2 14 27.4.5.6 1.5.6 2 0C26.9 42.2 39 27.4 39 17c0-8.3-6.7-15-15-15Z"/>SYMBOL</svg>';

  function fetchJson(path) {
    if (typeof window.fetch === "function") {
      return window.fetch(path).then(function (response) {
        if (!response.ok) {
          throw new Error("Falha ao carregar " + path);
        }
        return response.json();
      });
    }

    return new Promise(function (resolve, reject) {
      var request = new XMLHttpRequest();
      request.open("GET", path, true);
      request.onreadystatechange = function () {
        if (request.readyState !== 4) {
          return;
        }

        if (request.status >= 200 && request.status < 300) {
          try {
            resolve(JSON.parse(request.responseText));
          } catch (error) {
            reject(error);
          }
          return;
        }

        reject(new Error("Falha ao carregar " + path));
      };
      request.onerror = function () {
        reject(new Error("Falha ao carregar " + path));
      };
      request.send();
    });
  }

  function isMissingNumber(value) {
    return value === null || value === undefined || isNaN(Number(value));
  }

  function formatNumber(value, options) {
    if (isMissingNumber(value)) {
      return "0";
    }
    if (typeof Intl !== "undefined" && typeof Intl.NumberFormat === "function") {
      return new Intl.NumberFormat("pt-BR", options || {}).format(Number(value));
    }
    return String(Number(value));
  }

  function formatDensity(value) {
    if (isMissingNumber(value)) {
      return "n/d";
    }
    return (
      formatNumber(value, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }) + " hab/km²"
    );
  }

  function formatCoordinates(lat, lng) {
    if (isMissingNumber(lat) || isMissingNumber(lng)) {
      return "n/d";
    }
    return Number(lat).toFixed(5) + ", " + Number(lng).toFixed(5);
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function hexToRgba(hex, alpha) {
    var normalized = String(hex || "").replace("#", "");
    if (normalized.length === 3) {
      normalized =
        normalized.charAt(0) +
        normalized.charAt(0) +
        normalized.charAt(1) +
        normalized.charAt(1) +
        normalized.charAt(2) +
        normalized.charAt(2);
    }

    if (normalized.length !== 6) {
      return "rgba(37,99,235," + alpha + ")";
    }

    var r = parseInt(normalized.slice(0, 2), 16);
    var g = parseInt(normalized.slice(2, 4), 16);
    var b = parseInt(normalized.slice(4, 6), 16);
    return "rgba(" + r + "," + g + "," + b + "," + alpha + ")";
  }

  function extend(base, extra) {
    var result = {};
    var key;
    var sourceList = [base || {}, extra || {}];
    var index;

    for (index = 0; index < sourceList.length; index += 1) {
      for (key in sourceList[index]) {
        if (Object.prototype.hasOwnProperty.call(sourceList[index], key)) {
          result[key] = sourceList[index][key];
        }
      }
    }

    return result;
  }

  function matchesMedia(query, fallback) {
    if (typeof window.matchMedia !== "function") {
      return Boolean(fallback);
    }

    try {
      return window.matchMedia(query).matches;
    } catch (error) {
      return Boolean(fallback);
    }
  }

  function supportsHover() {
    return matchesMedia("(hover: hover)", false) && matchesMedia("(pointer: fine)", false);
  }

  function requestFrame(callback) {
    if (typeof window.requestAnimationFrame === "function") {
      return window.requestAnimationFrame(callback);
    }
    return window.setTimeout(callback, 16);
  }

  function scheduleMapResize(map) {
    if (!map) {
      return;
    }

    requestFrame(function () {
      map.invalidateSize({ pan: false, debounceMoveend: true });
    });
    window.setTimeout(function () {
      map.invalidateSize({ pan: false, debounceMoveend: true });
    }, 220);
  }

  function getActiveSchoolLayerIds(appState) {
    return Object.keys(appState.activeSchoolLayerIds || {}).filter(function (layerId) {
      return Boolean(appState.activeSchoolLayerIds[layerId]);
    });
  }

  function normalizeBoundsPadding(padding) {
    if (typeof padding === "number") {
      return {
        north: padding,
        south: padding,
        east: padding,
        west: padding,
      };
    }

    return {
      north: padding && padding.north != null ? Number(padding.north) : 0,
      south: padding && padding.south != null ? Number(padding.south) : 0,
      east: padding && padding.east != null ? Number(padding.east) : 0,
      west: padding && padding.west != null ? Number(padding.west) : 0,
    };
  }

  function expandBounds(bounds, padding) {
    var normalized = normalizeBoundsPadding(padding);
    var southWest = bounds.getSouthWest();
    var northEast = bounds.getNorthEast();
    var latSpan = Math.max(Math.abs(northEast.lat - southWest.lat), 0.01);
    var lngSpan = Math.max(Math.abs(northEast.lng - southWest.lng), 0.01);

    return L.latLngBounds(
      [
        southWest.lat - latSpan * normalized.south,
        southWest.lng - lngSpan * normalized.west,
      ],
      [
        northEast.lat + latSpan * normalized.north,
        northEast.lng + lngSpan * normalized.east,
      ]
    );
  }

  function normalizeViewportPadding(padding, fallback) {
    if (typeof padding === "number") {
      return {
        top: padding,
        right: padding,
        bottom: padding,
        left: padding,
      };
    }

    return {
      top: padding && padding.top != null ? Number(padding.top) : fallback,
      right: padding && padding.right != null ? Number(padding.right) : fallback,
      bottom: padding && padding.bottom != null ? Number(padding.bottom) : fallback,
      left: padding && padding.left != null ? Number(padding.left) : fallback,
    };
  }

  function getFitBoundsOptions(map, config) {
    var padding = normalizeViewportPadding(config.map.fitPadding, 20);
    var mapSize = typeof map.getSize === "function" ? map.getSize() : { x: 0, y: 0 };
    var extraBottom = shouldUseBottomControls()
      ? Math.round(mapSize.y * 0.04)
      : Math.round(mapSize.y * 0.11);

    return {
      animate: false,
      paddingTopLeft: [padding.left, padding.top],
      paddingBottomRight: [padding.right, padding.bottom + extraBottom],
    };
  }

  function getBoundsSpan(bounds) {
    var southWest = bounds.getSouthWest();
    var northEast = bounds.getNorthEast();
    return {
      lat: Math.abs(northEast.lat - southWest.lat),
      lng: Math.abs(northEast.lng - southWest.lng),
    };
  }

  function buildStateConstraintBounds(map, stateBounds, config) {
    var baseBounds = expandBounds(
      stateBounds,
      config.map.maxBoundsPadding == null
        ? { north: 0.24, south: 0.58, east: 0.24, west: 0.24 }
        : config.map.maxBoundsPadding
    );
    var viewBounds = typeof map.getBounds === "function" ? map.getBounds() : null;
    var slackFactor =
      config.map.maxBoundsViewportSlack == null ? 1.08 : config.map.maxBoundsViewportSlack;

    if (!viewBounds || !viewBounds.isValid()) {
      return baseBounds;
    }

    var baseSpan = getBoundsSpan(baseBounds);
    var viewSpan = getBoundsSpan(viewBounds);
    var requiredLatSpan = Math.max(baseSpan.lat, viewSpan.lat * slackFactor);
    var requiredLngSpan = Math.max(baseSpan.lng, viewSpan.lng * slackFactor);
    var extraLat = requiredLatSpan - baseSpan.lat;
    var extraLng = requiredLngSpan - baseSpan.lng;
    var southWest = baseBounds.getSouthWest();
    var northEast = baseBounds.getNorthEast();

    return L.latLngBounds(
      [southWest.lat - extraLat / 2, southWest.lng - extraLng / 2],
      [northEast.lat + extraLat / 2, northEast.lng + extraLng / 2]
    );
  }

  function applyStateConstraintBounds(map, stateBounds, config) {
    if (!stateBounds || !stateBounds.isValid()) {
      return null;
    }

    var constraintBounds = buildStateConstraintBounds(map, stateBounds, config);
    map.setMaxBounds(constraintBounds);
    return constraintBounds;
  }

  function shouldUseBottomControls() {
    var compactScreen = matchesMedia("(max-width: 760px)", window.innerWidth <= 760);
    var coarsePointer = matchesMedia("(pointer: coarse)", false);
    return compactScreen || coarsePointer;
  }

  function isCompactLayout() {
    return matchesMedia("(max-width: 1100px)", window.innerWidth <= 1100);
  }

  function setStatus(message) {
    document.getElementById("map-status").textContent = message;
  }

  function renderLayerControls(root, config) {
    var html = [];
    var layers = config.schoolLayers.concat([
      extend(config.densityLayer, { color: "#db6d30" }),
    ]);

    layers.forEach(function (layer) {
      var disabled = layer.status !== "ready" ? "disabled" : "";
      var checked = layer.defaultVisible ? "checked" : "";
      var chipClass = layer.status === "ready" ? "" : " layer-chip--disabled";
      var chipLabel = layer.status === "ready" ? "Disponível" : "Em preparação";
      html.push(
        '<article class="layer-toggle" data-layer-id="' +
          escapeHtml(layer.id) +
          '">' +
          '<div class="layer-toggle__meta">' +
          '<div class="layer-toggle__title-row">' +
          '<span class="layer-toggle__title">' +
          escapeHtml(layer.label) +
          "</span>" +
          '<span class="layer-chip' +
          chipClass +
          '" style="--chip-color:' +
          escapeHtml(layer.color || "#0f3551") +
          '">' +
          chipLabel +
          "</span>" +
          "</div>" +
          '<div class="layer-toggle__description">' +
          escapeHtml(layer.description) +
          "</div>" +
          "</div>" +
          '<label class="switch" aria-label="' +
          escapeHtml(layer.label) +
          '">' +
          '<input type="checkbox" data-toggle-id="' +
          escapeHtml(layer.id) +
          '" ' +
          disabled +
          " " +
          checked +
          " />" +
          '<span class="switch__track" style="--switch-color:' +
          escapeHtml(layer.color || "#0f3551") +
          '"></span>' +
          '<span class="switch__thumb"></span>' +
          "</label>" +
          "</article>"
      );
    });

    root.innerHTML = html.join("");
  }

  function updateSummary(payload) {
    document.getElementById("visible-school-count").textContent = formatNumber(
      payload.visibleSchoolCount
    );
    document.getElementById("active-layer-count").textContent = formatNumber(
      payload.activeLayerCount
    );
    document.getElementById("active-layer-chips").innerHTML = payload.activeChips;
    document.getElementById("active-layer-details").innerHTML = payload.details;
  }

  function renderDensityLegend(layerInstance) {
    var legendRoot = document.getElementById("density-legend");
    var scaleRoot = document.getElementById("density-legend-scale");
    var captionRoot = document.getElementById("density-legend-caption");
    var legend = layerInstance && layerInstance.metadata ? layerInstance.metadata.legend : [];

    if (!legend || !legend.length) {
      legendRoot.hidden = true;
      return;
    }

    scaleRoot.innerHTML = legend
      .map(function (item) {
        return (
          '<div class="density-legend__item">' +
          '<span class="density-legend__swatch" style="background:' +
          escapeHtml(item.color) +
          '"></span>' +
          "<span>" +
          escapeHtml(item.label) +
          "</span>" +
          "</div>"
        );
      })
      .join("");

    captionRoot.textContent =
      (layerInstance.metadata && layerInstance.metadata.source_note) ||
      "Densidade demográfica municipal oficial do IBGE.";
    legendRoot.hidden = false;
  }

  function hideDensityLegend() {
    document.getElementById("density-legend").hidden = true;
  }

  function closeSidebar(sidebar, button, map) {
    if (!sidebar.classList.contains("is-open")) {
      return;
    }
    sidebar.classList.remove("is-open");
    button.setAttribute("aria-expanded", "false");
    scheduleMapResize(map);
  }

  function attachPanelToggle(button, sidebar, map) {
    button.addEventListener("click", function () {
      var next = !sidebar.classList.contains("is-open");
      sidebar.classList.toggle("is-open", next);
      button.setAttribute("aria-expanded", String(next));
      scheduleMapResize(map);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closeSidebar(sidebar, button, map);
      }
    });
  }

  function buildActiveChips(appState, config) {
    var chips = [];
    getActiveSchoolLayerIds(appState).forEach(function (layerId) {
      var layerConfig = findSchoolLayer(config, layerId);
      if (!layerConfig) {
        return;
      }
      chips.push(
        '<span class="layer-chip" style="--chip-color:' +
          escapeHtml(layerConfig.color) +
          '">' +
          escapeHtml(layerConfig.label) +
          "</span>"
      );
    });

    if (appState.densityActive) {
      chips.push(
        '<span class="layer-chip" style="--chip-color:#db6d30">' +
          escapeHtml(config.densityLayer.label) +
          "</span>"
      );
    }

    if (!chips.length) {
      return '<span class="layer-chip layer-chip--disabled">Nenhuma camada ativa</span>';
    }

    return chips.join("");
  }

  function buildActiveDetails(appState, config) {
    var lines = [];

    getActiveSchoolLayerIds(appState).forEach(function (layerId) {
      var layerConfig = findSchoolLayer(config, layerId);
      var instance = appState.loadedSchoolLayers[layerId];
      if (!layerConfig || !instance) {
        return;
      }

      lines.push(
        "<p><strong>" +
          escapeHtml(layerConfig.label) +
          ":</strong> " +
          formatNumber(instance.featureCount) +
          " registros no mapa.</p>"
      );
    });

    if (appState.densityActive && appState.densityLayer) {
      lines.push(
        "<p><strong>" +
          escapeHtml(config.densityLayer.label) +
          ":</strong> " +
          formatNumber(appState.densityLayer.featureCount) +
          " municípios com densidade oficial do IBGE.</p>"
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
    var visibleSchoolCount = 0;
    var activeLayerIds = getActiveSchoolLayerIds(appState);

    activeLayerIds.forEach(function (layerId) {
      if (appState.activeSchoolLayerIds[layerId] && appState.loadedSchoolLayers[layerId]) {
        visibleSchoolCount += appState.loadedSchoolLayers[layerId].featureCount;
      }
    });

    updateSummary({
      visibleSchoolCount: visibleSchoolCount,
      activeLayerCount: activeLayerIds.length + (appState.densityActive ? 1 : 0),
      activeChips: buildActiveChips(appState, config),
      details: buildActiveDetails(appState, config),
    });
  }

  function findSchoolLayer(config, layerId) {
    for (var index = 0; index < config.schoolLayers.length; index += 1) {
      if (config.schoolLayers[index].id === layerId) {
        return config.schoolLayers[index];
      }
    }
    return null;
  }

  function createMap(config) {
    var map = L.map("map", {
      zoomControl: false,
      minZoom: config.map.minZoom,
      maxZoom: config.map.maxZoom,
      maxBoundsViscosity:
        config.map.maxBoundsViscosity == null ? 0.35 : config.map.maxBoundsViscosity,
      preferCanvas: true,
      worldCopyJump: false,
      zoomSnap: 0.5,
      wheelPxPerZoomLevel: 120,
      tapTolerance: 18,
      bounceAtZoomLimits: false,
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
      detectRetina: true,
      updateWhenIdle: true,
      updateWhenZooming: false,
      keepBuffer: shouldUseBottomControls() ? 2 : 3,
    }).addTo(map);

    var zoomControl = L.control.zoom({
      position: shouldUseBottomControls() ? "bottomright" : "topright",
    });
    zoomControl.addTo(map);

    function syncViewport() {
      zoomControl.setPosition(shouldUseBottomControls() ? "bottomright" : "topright");
      scheduleMapResize(map);
    }

    window.addEventListener("resize", syncViewport);
    window.addEventListener("orientationchange", function () {
      window.setTimeout(syncViewport, 120);
    });
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible") {
        syncViewport();
      }
    });

    map.setView(config.map.center, config.map.zoom);
    return map;
  }

  function coordinatesToLatLngs(ring) {
    return ring.map(function (coordinate) {
      return [coordinate[1], coordinate[0]];
    });
  }

  function extractStateHoles(geometry) {
    if (!geometry) {
      return [];
    }

    if (geometry.type === "Polygon") {
      return [coordinatesToLatLngs(geometry.coordinates[0])];
    }

    if (geometry.type === "MultiPolygon") {
      return geometry.coordinates.map(function (polygon) {
        return coordinatesToLatLngs(polygon[0]);
      });
    }

    return [];
  }

  function createStateFrame(map, stateConfig) {
    return fetchJson(stateConfig.dataPath).then(function (geojson) {
      var feature = geojson.features[0];
      var outlineLayer = L.geoJSON(geojson, {
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

      var maskHoles = extractStateHoles(feature && feature.geometry);
      var maskLayer = null;
      if (maskHoles.length > 0) {
        maskLayer = L.polygon(
          [
            [
              [89, -360],
              [89, 360],
              [-89, 360],
              [-89, -360],
            ],
          ].concat(maskHoles),
          {
            pane: "stateMaskPane",
            stroke: false,
            fillColor: stateConfig.maskColor,
            fillOpacity: stateConfig.maskOpacity,
            interactive: false,
          }
        );
      }

      return {
        source: geojson,
        outlineLayer: outlineLayer,
        maskLayer: maskLayer,
        bounds: outlineLayer.getBounds(),
      };
    });
  }

  function buildSchoolMarkerIcon(layerConfig) {
    var symbol = LAYER_SYMBOLS[layerConfig.id] || LAYER_SYMBOLS.estaduais;
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
      html:
        '<div class="school-cluster" style="--cluster-fill:' +
        escapeHtml(hexToRgba(color, 0.8)) +
        '"><span>' +
        count +
        "</span></div>",
      iconSize: [38, 38],
    });
  }

  function buildAddress(properties) {
    var parts = [
      [properties.address, properties.number].filter(Boolean).join(", "),
      properties.district,
      properties.municipio,
      properties.uf,
      properties.postal_code,
    ].filter(Boolean);
    return parts.join(" · ");
  }

  function buildPopupMarkup(properties, layerConfig) {
    var activeStatus =
      properties.status && String(properties.status).toLowerCase() === "em atividade";
    var statusClass = activeStatus ? "" : " is-inactive";

    return (
      '<article class="school-popup">' +
      '<header class="school-popup__heading">' +
      "<h3>" +
      escapeHtml(properties.name) +
      "</h3>" +
      '<div class="school-popup__badges">' +
      '<span class="popup-badge">' +
      escapeHtml(layerConfig.label) +
      "</span>" +
      '<span class="popup-badge popup-badge--status' +
      statusClass +
      '">' +
      escapeHtml(properties.status || "Sem status") +
      "</span>" +
      "</div>" +
      "</header>" +
      '<div class="school-popup__grid">' +
      '<div class="school-popup__row"><span class="school-popup__label">Município</span><span class="school-popup__value">' +
      escapeHtml(properties.municipio || "n/d") +
      "</span></div>" +
      '<div class="school-popup__row"><span class="school-popup__label">Endereço</span><span class="school-popup__value">' +
      escapeHtml(buildAddress(properties) || "n/d") +
      "</span></div>" +
      '<div class="school-popup__row"><span class="school-popup__label">Georreferenciamento</span><span class="school-popup__value">' +
      escapeHtml(properties.classification || "n/d") +
      " · " +
      escapeHtml(properties.georef_source || "n/d") +
      "</span></div>" +
      '<div class="school-popup__row"><span class="school-popup__label">Coordenadas</span><span class="school-popup__value">' +
      escapeHtml(formatCoordinates(properties.latitude, properties.longitude)) +
      "</span></div>" +
      '<div class="school-popup__row"><span class="school-popup__label">Contato</span><span class="school-popup__value">' +
      escapeHtml(properties.phone_primary || properties.email || "n/d") +
      "</span></div>" +
      "</div>" +
      "</article>"
    );
  }

  function createSchoolLayer(map, layerConfig) {
    return fetchJson(layerConfig.dataPath).then(function (geojson) {
      var features = Array.isArray(geojson.features) ? geojson.features : [];
      var icon = buildSchoolMarkerIcon(layerConfig);
      var allowTooltip = supportsHover();
      var popupMaxWidth = isCompactLayout() ? 280 : 320;
      var clusterGroup = L.markerClusterGroup({
        showCoverageOnHover: false,
        spiderfyOnMaxZoom: true,
        chunkedLoading: true,
        removeOutsideVisibleBounds: true,
        animate: !matchesMedia("(prefers-reduced-motion: reduce)", false),
        maxClusterRadius: shouldUseBottomControls() ? 38 : 46,
        zoomToBoundsOnClick: true,
        iconCreateFunction: function (cluster) {
          return buildClusterIcon(layerConfig.color, cluster.getChildCount());
        },
      });

      var featureLayer = L.geoJSON(geojson, {
        pointToLayer: function (feature, latlng) {
          return L.marker(latlng, { icon: icon, keyboard: true });
        },
        onEachFeature: function (feature, marker) {
          var properties = feature.properties || {};
          marker.bindPopup(buildPopupMarkup(properties, layerConfig), {
            maxWidth: popupMaxWidth,
          });
          if (allowTooltip) {
            marker.bindTooltip(escapeHtml(properties.name || layerConfig.label), {
              direction: "top",
              offset: [0, -18],
            });
          }
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
    });
  }

  function styleDensityFeature(feature, metadata) {
    var classes = metadata && metadata.legend ? metadata.legend : [];
    var index = Number(feature.properties && feature.properties.density_class ? feature.properties.density_class : 0);
    var bucket = classes[Math.max(0, Math.min(index, classes.length - 1))];
    var fillColor = bucket && bucket.color ? bucket.color : "#d9d9d9";
    return {
      pane: "densityPane",
      color: "rgba(18, 53, 77, 0.24)",
      weight: 1,
      fillColor: fillColor,
      fillOpacity: 0.72,
    };
  }

  function buildDensityPopup(feature) {
    var properties = feature.properties || {};
    return (
      '<article class="school-popup">' +
      '<header class="school-popup__heading">' +
      "<h3>" +
      escapeHtml(properties.municipio_nome || "Município") +
      "</h3>" +
      '<div class="school-popup__badges"><span class="popup-badge">Densidade populacional</span></div>' +
      "</header>" +
      '<div class="school-popup__grid">' +
      '<div class="school-popup__row"><span class="school-popup__label">Densidade</span><span class="school-popup__value">' +
      escapeHtml(formatDensity(properties.densidade_demografica)) +
      "</span></div>" +
      '<div class="school-popup__row"><span class="school-popup__label">População no Censo 2022</span><span class="school-popup__value">' +
      escapeHtml(formatNumber(properties.populacao_censo_2022) + " pessoas") +
      "</span></div>" +
      '<div class="school-popup__row"><span class="school-popup__label">Área Territorial</span><span class="school-popup__value">' +
      escapeHtml(
        formatNumber(properties.area_territorial_km2, {
          minimumFractionDigits: 3,
          maximumFractionDigits: 3,
        }) + " km²"
      ) +
      "</span></div>" +
      "</div>" +
      "</article>"
    );
  }

  function createDensityLayer(map, densityConfig) {
    return fetchJson(densityConfig.dataPath).then(function (geojson) {
      var metadata = geojson.metadata || {};
      var allowTooltip = supportsHover();
      var popupMaxWidth = isCompactLayout() ? 280 : 320;
      var layer = L.geoJSON(geojson, {
        style: function (feature) {
          return styleDensityFeature(feature, metadata);
        },
        onEachFeature: function (feature, subLayer) {
          var originalStyle = styleDensityFeature(feature, metadata);

          subLayer.bindPopup(buildDensityPopup(feature), {
            maxWidth: popupMaxWidth,
          });
          if (allowTooltip) {
            subLayer.bindTooltip(
              (feature.properties ? feature.properties.municipio_nome : "Município") +
                " · " +
                formatDensity(feature.properties ? feature.properties.densidade_demografica : null),
              { sticky: true, className: "density-tooltip" }
            );
          }

          subLayer.on("mouseover", function () {
            subLayer.setStyle(
              extend(originalStyle, {
                weight: 2,
                fillOpacity: 0.9,
                color: "rgba(18, 53, 77, 0.45)",
              })
            );
          });

          subLayer.on("mouseout", function () {
            subLayer.setStyle(originalStyle);
          });
        },
      });

      return {
        id: densityConfig.id,
        label: densityConfig.label,
        source: geojson,
        metadata: metadata,
        layer: layer,
        featureCount: Array.isArray(geojson.features) ? geojson.features.length : 0,
        bounds: layer.getBounds(),
      };
    });
  }

  function toggleSchoolLayer(options) {
    var layerConfig = findSchoolLayer(options.config, options.layerId);
    if (!layerConfig || layerConfig.status !== "ready") {
      return Promise.resolve();
    }

    if (options.enabled) {
      if (options.appState.loadedSchoolLayers[options.layerId]) {
        var loadedInstance = options.appState.loadedSchoolLayers[options.layerId];
        if (!options.map.hasLayer(loadedInstance.layer)) {
          loadedInstance.layer.addTo(options.map);
        }
        options.appState.activeSchoolLayerIds[options.layerId] = true;
        refreshSummary(options.appState, options.config);
        setStatus(layerConfig.label + " ativa.");
        return Promise.resolve();
      }

      setStatus("Carregando " + layerConfig.label.toLowerCase() + "...");
      return createSchoolLayer(options.map, layerConfig).then(function (instance) {
        options.appState.loadedSchoolLayers[options.layerId] = instance;
        options.appState.activeSchoolLayerIds[options.layerId] = true;
        instance.layer.addTo(options.map);
        refreshSummary(options.appState, options.config);
        setStatus(layerConfig.label + " ativa.");
      });
    }

    if (
      options.appState.loadedSchoolLayers[options.layerId] &&
      options.map.hasLayer(options.appState.loadedSchoolLayers[options.layerId].layer)
    ) {
      options.map.removeLayer(options.appState.loadedSchoolLayers[options.layerId].layer);
    }
    delete options.appState.activeSchoolLayerIds[options.layerId];
    refreshSummary(options.appState, options.config);
    setStatus(layerConfig.label + " oculta.");
    return Promise.resolve();
  }

  function toggleDensityLayer(options) {
    if (options.enabled) {
      if (options.appState.densityLayer) {
        if (!options.map.hasLayer(options.appState.densityLayer.layer)) {
          options.appState.densityLayer.layer.addTo(options.map);
          options.appState.densityLayer.layer.bringToBack();
        }
        options.appState.densityActive = true;
        renderDensityLegend(options.appState.densityLayer);
        refreshSummary(options.appState, options.config);
        setStatus("Densidade populacional ativa.");
        return Promise.resolve();
      }

      setStatus("Carregando densidade populacional...");
      return createDensityLayer(options.map, options.config.densityLayer).then(function (instance) {
        options.appState.densityLayer = instance;
        options.appState.densityActive = true;
        instance.layer.addTo(options.map);
        instance.layer.bringToBack();
        renderDensityLegend(instance);
        refreshSummary(options.appState, options.config);
        setStatus("Densidade populacional ativa.");
      });
    }

    if (options.appState.densityLayer && options.map.hasLayer(options.appState.densityLayer.layer)) {
      options.map.removeLayer(options.appState.densityLayer.layer);
    }
    options.appState.densityActive = false;
    hideDensityLegend();
    refreshSummary(options.appState, options.config);
    setStatus("Densidade populacional oculta.");
    return Promise.resolve();
  }

  function bootstrap() {
    fetchJson(CONFIG_PATH)
      .then(function (config) {
        var map = createMap(config);
        var sidebar = document.getElementById("sidebar");
        var panelToggle = document.getElementById("panel-toggle");
        var syncStateConstraintBounds = function () {};
        var appState = {
          loadedSchoolLayers: {},
          activeSchoolLayerIds: {},
          densityLayer: null,
          densityActive: false,
        };

        attachPanelToggle(panelToggle, sidebar, map);
        renderLayerControls(document.getElementById("layer-controls"), config);

        map.on("click movestart zoomstart", function () {
          if (isCompactLayout()) {
            closeSidebar(sidebar, panelToggle, map);
          }
        });

        createStateFrame(map, config.stateBoundary)
          .then(function (stateFrame) {
            if (stateFrame.maskLayer) {
              stateFrame.maskLayer.addTo(map);
            }
            stateFrame.outlineLayer.addTo(map);

            if (stateFrame.bounds && stateFrame.bounds.isValid()) {
              map.fitBounds(stateFrame.bounds, getFitBoundsOptions(map, config));
              syncStateConstraintBounds = function () {
                applyStateConstraintBounds(map, stateFrame.bounds, config);
              };
              syncStateConstraintBounds();
              map.on("zoomend", syncStateConstraintBounds);
              map.on("resize", syncStateConstraintBounds);
            }
            scheduleMapResize(map);
            window.setTimeout(syncStateConstraintBounds, 260);
          })
          .catch(function (error) {
            console.error(error);
            setStatus("Falha ao carregar o contorno do estado.");
          });

        var toggles = Array.prototype.slice.call(
          document.querySelectorAll("[data-toggle-id]")
        );
        toggles.forEach(function (toggle) {
          toggle.addEventListener("change", function (event) {
            var target = event.currentTarget;
            var layerId = target.getAttribute("data-toggle-id");
            var schoolLayer = findSchoolLayer(config, layerId);
            var shouldRestoreToggle = schoolLayer
              ? schoolLayer.status === "ready"
              : config.densityLayer.status === "ready";

            target.disabled = true;
            var promise = schoolLayer
              ? toggleSchoolLayer({
                  map: map,
                  appState: appState,
                  config: config,
                  layerId: layerId,
                  enabled: target.checked,
                })
              : toggleDensityLayer({
                  map: map,
                  appState: appState,
                  config: config,
                  enabled: target.checked,
                });

            promise.then(
              function () {
                if (shouldRestoreToggle) {
                  target.disabled = false;
                }
                scheduleMapResize(map);
              },
              function (error) {
                target.checked = false;
                if (shouldRestoreToggle) {
                  target.disabled = false;
                }
                setStatus(error.message || "Falha ao alternar a camada.");
              }
            );
          });
        });

        refreshSummary(appState, config);

        config.schoolLayers
          .filter(function (item) {
            return item.status === "ready" && item.defaultVisible;
          })
          .reduce(function (chain, layerConfig) {
            return chain.then(function () {
              return toggleSchoolLayer({
                map: map,
                appState: appState,
                config: config,
                layerId: layerConfig.id,
                enabled: true,
              });
            });
          }, Promise.resolve())
          .then(function () {
            if (config.densityLayer.defaultVisible) {
              return toggleDensityLayer({
                map: map,
                appState: appState,
                config: config,
                enabled: true,
              });
            }
            return Promise.resolve();
          })
          .then(function () {
            setStatus("Mapa pronto.");
          })
          .catch(function (error) {
            console.error(error);
            setStatus(error.message || "Falha ao iniciar o mapa.");
          });
      })
      .catch(function (error) {
        console.error(error);
        setStatus("Falha ao iniciar o mapa.");
      });
  }

  bootstrap();
})();
