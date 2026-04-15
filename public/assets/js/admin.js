(function () {
  "use strict";

  var API_BASE = "/api";
  var PAGE_SIZE = 50;
  var NETWORK_LABELS = {
    municipais: "E. Municipais",
    estaduais: "E. Estaduais",
    federais: "E. Federais",
    privadas: "E. Privadas",
  };
  var STATIC_DATASETS = [
    { id: "municipais", path: "../data/schools/e_municipais.json" },
    { id: "estaduais", path: "../data/schools/e_estaduais.json" },
    { id: "federais", path: "../data/schools/e_federais.json" },
    { id: "privadas", path: "../data/schools/e_privadas.json" },
  ];
  var ROW_FIELDS = [
    "network_type",
    "inep_code",
    "name",
    "name_original",
    "municipio",
    "uf",
    "status",
    "address",
    "number",
    "complement",
    "district",
    "postal_code",
    "latitude",
    "longitude",
    "detail_shard",
    "teacher_count",
    "student_count",
    "classification",
    "display_type",
    "institution",
    "acronym",
    "phone_primary",
    "email",
    "georef_source",
    "teacher_estimated",
    "student_estimated",
    "estimate_note",
    "notes",
  ];

  var state = {
    apiEnabled: false,
    readOnly: false,
    controlsDisabled: false,
    editingRowId: "",
    openNotesRowId: "",
    notePositionFrame: 0,
    page: 0,
    total: 0,
    serverTotal: 0,
    serverItems: [],
    items: [],
    staticItems: [],
    draftRows: [],
    nextDraftId: 1,
    syncingScroll: false,
    options: {
      networkTypes: [],
      municipios: [],
    },
    filters: {
      q: "",
      network_type: "",
      municipio: "",
    },
  };

  function fetchJson(path, options) {
    return window.fetch(path, options || {}).then(function (response) {
      if (!response.ok) {
        return response
          .json()
          .catch(function () {
            return {};
          })
          .then(function (payload) {
            throw new Error(payload.error || "Falha ao carregar dados.");
          });
      }
      return response.json();
    });
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function cleanText(value) {
    var text = String(value == null ? "" : value).trim();
    if (!text) {
      return "";
    }
    switch (text.toLowerCase()) {
      case "null":
      case "undefined":
      case "nan":
        return "";
      default:
        return text;
    }
  }

  function normalizeSearchText(value) {
    return cleanText(value)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();
  }

  function setStatus(message, tone) {
    var banner = document.getElementById("status-banner");
    banner.textContent = message;
    if (tone) {
      banner.setAttribute("data-tone", tone);
    } else {
      banner.removeAttribute("data-tone");
    }
  }

  function setModeCopy(text) {
    document.getElementById("admin-mode-copy").textContent = text;
  }

  function setBaseControlsDisabled(disabled) {
    state.controlsDisabled = disabled;
    syncInteractiveState();
  }

  function syncInteractiveState() {
    var editingLocked = !!state.editingRowId && state.apiEnabled;
    var disableToolbar = state.controlsDisabled || editingLocked;
    var disableNewSchool = state.controlsDisabled || !state.apiEnabled || editingLocked;

    [
      "search-input",
      "network-filter",
      "municipio-filter",
      "refresh-button",
    ].forEach(function (id) {
      var element = document.getElementById(id);
      if (element) {
        element.disabled = disableToolbar;
      }
    });

    document.getElementById("new-school-button").disabled = disableNewSchool;
  }

  function fillSelect(select, items, placeholder, valueKey, labelKey) {
    var html = ['<option value="">' + escapeHtml(placeholder) + "</option>"];
    items.forEach(function (item) {
      html.push(
        '<option value="' +
          escapeHtml(item[valueKey]) +
          '">' +
          escapeHtml(item[labelKey]) +
          "</option>"
      );
    });
    select.innerHTML = html.join("");
  }

  function renderOptions() {
    fillSelect(
      document.getElementById("network-filter"),
      state.options.networkTypes,
      "Todas",
      "id",
      "label"
    );
    fillSelect(
      document.getElementById("municipio-filter"),
      state.options.municipios.map(function (item) {
        return { id: item, label: item };
      }),
      "Todos",
      "id",
      "label"
    );
  }

  function getRowId(item) {
    return item._draftId || item.id;
  }

  function getVisibleNetworkOptions() {
    if (state.options.networkTypes.length) {
      return state.options.networkTypes;
    }
    return STATIC_DATASETS.map(function (item) {
      return { id: item.id, label: NETWORK_LABELS[item.id] };
    });
  }

  function getDisplayValue(item, field) {
    if (field === "network_type") {
      return NETWORK_LABELS[item.network_type] || cleanText(item.network_type) || "—";
    }
    if (field === "name") {
      return cleanText(item.name) || cleanText(item.name_original) || "Escola sem nome";
    }
    return cleanText(item[field]) || "—";
  }

  function isRowEditable(item) {
    return item._isDraft || state.editingRowId === getRowId(item);
  }

  function canStartEditing(item) {
    return state.apiEnabled && !state.readOnly && !state.editingRowId && !item._isDraft;
  }

  function isNotesOpen(item) {
    return state.openNotesRowId === getRowId(item);
  }

  function buildStaticCell(value, extraClass) {
    return (
      '<div class="sheet-static' +
      (extraClass ? " " + extraClass : "") +
      '">' +
      escapeHtml(value) +
      "</div>"
    );
  }

  function buildSelectField(rowId, field, value, options) {
    var html = [
      '<select class="sheet-select" data-row-id="',
      escapeHtml(rowId),
      '" data-field="',
      escapeHtml(field),
      '">',
    ];
    options.forEach(function (option) {
      html.push(
        '<option value="' +
          escapeHtml(option.id) +
          '"' +
          (cleanText(value) === option.id ? " selected" : "") +
          ">" +
          escapeHtml(option.label) +
          "</option>"
      );
    });
    html.push("</select>");
    return html.join("");
  }

  function buildInputField(rowId, field, value, type, attrs) {
    return (
      '<input class="sheet-input" data-row-id="' +
      escapeHtml(rowId) +
      '" data-field="' +
      escapeHtml(field) +
      '" type="' +
      escapeHtml(type || "text") +
      '" value="' +
      escapeHtml(cleanText(value)) +
      '"' +
      (attrs ? " " + attrs : "") +
      " />"
    );
  }

  function buildTextareaField(rowId, field, value) {
    return (
      '<textarea class="sheet-textarea" data-row-id="' +
      escapeHtml(rowId) +
      '" data-field="' +
      escapeHtml(field) +
      '">' +
      escapeHtml(cleanText(value)) +
      "</textarea>"
    );
  }

  function buildNotesCell(item) {
    var rowId = getRowId(item);
    var editing = isRowEditable(item);
    var notesValue = cleanText(item.notes);
    var hasNotes = !!notesValue;
    var popoverClass = "sheet-note-popover" + (isNotesOpen(item) ? " is-open" : "");
    var buttonLabel = editing
      ? hasNotes
        ? "Editar nota"
        : "Adicionar nota"
      : "Ver notas";
    var buttonClass = "sheet-note-toggle" + (editing && !hasNotes ? " sheet-note-toggle--text" : "");
    var body;

    if (!editing && !hasNotes) {
      return buildStaticCell("—");
    }

    if (editing) {
      body = buildTextareaField(rowId, "notes", item.notes);
    } else {
      body = '<div class="sheet-note-text">' + escapeHtml(notesValue || "Sem notas para esta escola.") + "</div>";
    }

    return (
      '<div class="sheet-note-cell">' +
      '<button class="' +
      buttonClass +
      '" type="button" data-action="toggle-notes" data-row-id="' +
      escapeHtml(rowId) +
      '" aria-label="' +
      escapeHtml(buttonLabel) +
      '" aria-expanded="' +
      String(isNotesOpen(item)) +
      '">' +
      (editing && !hasNotes
        ? '<span>Adicionar</span>'
        : '<span aria-hidden="true">i</span>') +
      "</button>" +
      '<div class="' +
      popoverClass +
      '">' +
      body +
      "</div>" +
      "</div>"
    );
  }

  function clampNumber(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function positionOpenNotesPopover() {
    var rowId = state.openNotesRowId;
    var button;
    var popover;
    var buttonRect;
    var viewportWidth;
    var viewportHeight;
    var popoverWidth;
    var popoverHeight;
    var margin = 12;
    var gap = 10;
    var openAbove;
    var left;
    var top;

    if (!rowId) {
      return;
    }

    button = document.querySelector(
      '[data-action="toggle-notes"][data-row-id="' + rowId + '"]'
    );
    popover = button && button.parentNode
      ? button.parentNode.querySelector(".sheet-note-popover.is-open")
      : null;

    if (!button || !popover) {
      return;
    }

    buttonRect = button.getBoundingClientRect();
    viewportWidth = window.innerWidth || document.documentElement.clientWidth;
    viewportHeight = window.innerHeight || document.documentElement.clientHeight;
    popoverWidth = popover.offsetWidth;
    popoverHeight = popover.offsetHeight;
    openAbove =
      buttonRect.bottom + gap + popoverHeight + margin > viewportHeight &&
      buttonRect.top - gap - popoverHeight - margin >= 0;

    left = clampNumber(
      buttonRect.left + buttonRect.width / 2 - popoverWidth / 2,
      margin,
      Math.max(margin, viewportWidth - popoverWidth - margin)
    );
    top = openAbove
      ? buttonRect.top - popoverHeight - gap
      : buttonRect.bottom + gap;
    top = clampNumber(
      top,
      margin,
      Math.max(margin, viewportHeight - popoverHeight - margin)
    );

    popover.style.left = String(Math.round(left)) + "px";
    popover.style.top = String(Math.round(top)) + "px";
    popover.setAttribute("data-placement", openAbove ? "top" : "bottom");
  }

  function scheduleOpenNotesPosition() {
    if (state.notePositionFrame) {
      return;
    }
    state.notePositionFrame = window.requestAnimationFrame(function () {
      state.notePositionFrame = 0;
      positionOpenNotesPopover();
    });
  }

  function buildFieldCell(item, field, config) {
    var rowId = getRowId(item);

    if (field === "notes") {
      return buildNotesCell(item);
    }

    if (!isRowEditable(item)) {
      return buildStaticCell(getDisplayValue(item, field), config.staticClass || "");
    }

    if (config.kind === "select") {
      return buildSelectField(rowId, field, item[field], config.options());
    }
    if (config.kind === "textarea") {
      return buildTextareaField(rowId, field, item[field]);
    }
    return buildInputField(rowId, field, item[field], config.type, config.attrs);
  }

  function buildActionCell(item) {
    var rowId = getRowId(item);
    var editing = isRowEditable(item);
    var html = ['<div class="sheet-actions">'];

    if (state.readOnly || !state.apiEnabled) {
      html.push('<div class="sheet-row-meta">Somente leitura</div>');
      html.push("</div>");
      return html.join("");
    }

    if (item._isDraft) {
      html.push(
        '<button class="primary-button sheet-action-button" type="button" data-action="save-row" data-row-id="' +
          escapeHtml(rowId) +
          '">Salvar</button>'
      );
      html.push(
        '<button class="ghost-link sheet-action-button" type="button" data-action="discard-row" data-row-id="' +
          escapeHtml(rowId) +
          '">Descartar</button>'
      );
      html.push('<div class="sheet-row-meta">Nova escola</div>');
      html.push("</div>");
      return html.join("");
    }

    if (editing) {
      html.push(
        '<button class="primary-button sheet-action-button" type="button" data-action="save-row" data-row-id="' +
          escapeHtml(rowId) +
          '">Salvar</button>'
      );
      html.push(
        '<button class="ghost-link sheet-action-button" type="button" data-action="cancel-edit" data-row-id="' +
          escapeHtml(rowId) +
          '">Cancelar</button>'
      );
      html.push(
        '<button class="danger-button sheet-action-button" type="button" data-action="delete-row" data-row-id="' +
          escapeHtml(rowId) +
          '">Excluir</button>'
      );
    } else {
      html.push(
        '<button class="ghost-link sheet-action-button" type="button" data-action="edit-row" data-row-id="' +
          escapeHtml(rowId) +
          '"' +
          (canStartEditing(item) ? "" : " disabled") +
          ">Editar</button>"
      );
    }

    html.push('<div class="sheet-row-meta">' + escapeHtml(item.id || "Sem id") + "</div>");
    html.push("</div>");
    return html.join("");
  }

  function buildSchoolTableRowMarkup(item) {
    return (
      '<tr class="school-table__row' +
      (item._isDraft ? " is-draft" : "") +
      (isRowEditable(item) ? " is-editing" : "") +
      '" data-row-id="' +
      escapeHtml(getRowId(item)) +
      '">' +
      "<td>" +
      buildFieldCell(item, "name", { kind: "input", type: "text", attrs: 'required="required"', staticClass: "sheet-name" }) +
      "</td>" +
      "<td>" +
      buildActionCell(item) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "network_type", { kind: "select", options: getVisibleNetworkOptions, staticClass: "sheet-badge-host" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "inep_code", { kind: "input", type: "text" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "name_original", { kind: "input", type: "text" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "municipio", { kind: "input", type: "text", attrs: 'required="required"' }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "uf", { kind: "input", type: "text", attrs: 'maxlength="2"' }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "status", { kind: "input", type: "text" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "address", { kind: "input", type: "text" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "number", { kind: "input", type: "text" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "complement", { kind: "input", type: "text" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "district", { kind: "input", type: "text" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "postal_code", { kind: "input", type: "text" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "latitude", { kind: "input", type: "number", attrs: 'step="0.000001"' }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "longitude", { kind: "input", type: "number", attrs: 'step="0.000001"' }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "detail_shard", { kind: "input", type: "text" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "teacher_count", { kind: "input", type: "number", attrs: 'step="1" min="0"' }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "student_count", { kind: "input", type: "number", attrs: 'step="1" min="0"' }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "classification", { kind: "input", type: "text" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "display_type", { kind: "input", type: "text" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "institution", { kind: "input", type: "text" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "acronym", { kind: "input", type: "text" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "phone_primary", { kind: "input", type: "text" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "email", { kind: "input", type: "email" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "georef_source", { kind: "input", type: "text" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "teacher_estimated", { kind: "input", type: "text" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "student_estimated", { kind: "input", type: "text" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "estimate_note", { kind: "textarea" }) +
      "</td>" +
      "<td>" +
      buildFieldCell(item, "notes", { kind: "textarea" }) +
      "</td>" +
      "</tr>"
    );
  }

  function syncSheetScrollbar() {
    var sheet = document.querySelector(".school-sheet");
    var table = document.querySelector(".school-table");
    var bar = document.getElementById("sheet-scrollbar");
    var fill = document.getElementById("sheet-scrollbar-fill");
    if (!sheet || !table || !bar || !fill) {
      return;
    }
    fill.style.width = String(table.scrollWidth) + "px";
    bar.scrollLeft = sheet.scrollLeft;
  }

  function renderList() {
    var tableBody = document.getElementById("school-table-body");
    var visibleBase = state.page * PAGE_SIZE + 1;
    var start = state.total ? visibleBase : 0;
    var end = state.total ? Math.min(state.total, state.page * PAGE_SIZE + state.items.length) : 0;
    var hasOpenNotesRow = state.items.some(function (item) {
      return getRowId(item) === state.openNotesRowId;
    });

    if (!hasOpenNotesRow) {
      state.openNotesRowId = "";
    }

    document.getElementById("result-count").textContent = state.total + " escolas";
    document.getElementById("result-range").textContent =
      state.total && state.items.length
        ? "Mostrando " + start + " a " + end + "."
        : "Nenhum resultado para os filtros atuais.";
    document.getElementById("prev-page-button").disabled = state.page <= 0 || state.controlsDisabled || !!state.editingRowId;
    document.getElementById("next-page-button").disabled =
      state.page * PAGE_SIZE + state.serverItems.length >= state.serverTotal ||
      state.controlsDisabled ||
      !!state.editingRowId;

    if (!state.items.length) {
      state.openNotesRowId = "";
      tableBody.innerHTML =
        '<tr class="school-table__empty"><td colspan="29">Nenhuma escola encontrada com os filtros atuais.</td></tr>';
      syncInteractiveState();
      window.requestAnimationFrame(function () {
        syncSheetScrollbar();
        positionOpenNotesPopover();
      });
      return;
    }

    tableBody.innerHTML = state.items.map(buildSchoolTableRowMarkup).join("");
    syncInteractiveState();
    window.requestAnimationFrame(function () {
      syncSheetScrollbar();
      positionOpenNotesPopover();
    });
  }

  function updateFilterState() {
    state.filters.q = document.getElementById("search-input").value.trim();
    state.filters.network_type = document.getElementById("network-filter").value;
    state.filters.municipio = document.getElementById("municipio-filter").value;
  }

  function emptySchoolDraft() {
    return {
      id: "",
      _draftId: "draft-" + String(state.nextDraftId++),
      _isDraft: true,
      network_type: state.filters.network_type || "municipais",
      inep_code: "",
      name: "",
      name_original: "",
      municipio: state.filters.municipio || "",
      uf: "ES",
      status: "",
      address: "",
      number: "",
      complement: "",
      district: "",
      postal_code: "",
      classification: "",
      display_type: "",
      institution: "",
      acronym: "",
      georef_source: "",
      phone_primary: "",
      email: "",
      teacher_count: "",
      student_count: "",
      teacher_estimated: "",
      student_estimated: "",
      estimate_note: "",
      notes: "",
      latitude: "",
      longitude: "",
      detail_shard: "",
    };
  }

  function normalizeStaticRecord(record, networkId, index) {
    return {
      id: networkId + "-static-" + String(index + 1),
      network_type: networkId,
      inep_code: "",
      name: cleanText(record.Nome_escola),
      name_original: cleanText(record.Nome_escola),
      municipio: cleanText(record.Municipio),
      uf: "ES",
      status: "",
      address: cleanText(record.Endereco),
      number: "",
      complement: "",
      district: "",
      postal_code: cleanText(record.CEP),
      classification: "",
      display_type: "",
      institution: "",
      acronym: "",
      georef_source: "",
      phone_primary: cleanText(record.telefone),
      email: cleanText(record.email),
      teacher_count: cleanText(record.Numero_professores),
      student_count: cleanText(record.Numero_alunos),
      teacher_estimated: "",
      student_estimated: "",
      estimate_note: "",
      notes: "",
      latitude: cleanText(record.Latitude),
      longitude: cleanText(record.Longitude),
      detail_shard: "",
    };
  }

  function matchesActiveFilters(item) {
    var matchesNetwork =
      !state.filters.network_type || item.network_type === state.filters.network_type;
    var matchesMunicipio =
      !state.filters.municipio ||
      normalizeSearchText(item.municipio) === normalizeSearchText(state.filters.municipio);
    var searchTarget = normalizeSearchText(
      [
        item.name,
        item.name_original,
        item.municipio,
        item.address,
        item.inep_code,
        item.email,
      ].join(" ")
    );
    var matchesSearch =
      !state.filters.q || searchTarget.indexOf(normalizeSearchText(state.filters.q)) >= 0;
    return matchesNetwork && matchesMunicipio && matchesSearch;
  }

  function mergeDraftRows(serverItems, totalBase) {
    var visibleDrafts = state.draftRows.filter(matchesActiveFilters);
    state.serverItems = serverItems.slice();
    state.serverTotal = totalBase;
    state.items = visibleDrafts.concat(serverItems);
    state.total = totalBase + visibleDrafts.length;
  }

  function loadStaticDatasets() {
    return Promise.all(
      STATIC_DATASETS.map(function (dataset) {
        return fetchJson(dataset.path).then(function (items) {
          return (Array.isArray(items) ? items : []).map(function (item, index) {
            return normalizeStaticRecord(item, dataset.id, index);
          });
        });
      })
    ).then(function (groups) {
      state.staticItems = groups.reduce(function (all, group) {
        return all.concat(group);
      }, []);
      state.options = {
        networkTypes: STATIC_DATASETS.map(function (item) {
          return {
            id: item.id,
            label: NETWORK_LABELS[item.id],
            schoolCount: state.staticItems.filter(function (school) {
              return school.network_type === item.id;
            }).length,
          };
        }),
        municipios: Array.from(
          new Set(
            state.staticItems
              .map(function (item) {
                return item.municipio;
              })
              .filter(Boolean)
          )
        ).sort(function (left, right) {
          return normalizeSearchText(left).localeCompare(normalizeSearchText(right));
        }),
      };
    });
  }

  function filterStaticItems() {
    var filtered = state.staticItems.filter(matchesActiveFilters);
    filtered.sort(function (left, right) {
      return normalizeSearchText(left.municipio + " " + left.name).localeCompare(
        normalizeSearchText(right.municipio + " " + right.name)
      );
    });
    mergeDraftRows(
      filtered.slice(state.page * PAGE_SIZE, state.page * PAGE_SIZE + PAGE_SIZE),
      filtered.length
    );
  }

  function loadList() {
    updateFilterState();
    if (!state.apiEnabled) {
      filterStaticItems();
      renderList();
      return Promise.resolve();
    }

    return fetchJson(
      API_BASE +
        "/schools?q=" +
        encodeURIComponent(state.filters.q) +
        "&network_type=" +
        encodeURIComponent(state.filters.network_type) +
        "&municipio=" +
        encodeURIComponent(state.filters.municipio) +
        "&limit=" +
        PAGE_SIZE +
        "&offset=" +
        state.page * PAGE_SIZE
    ).then(function (payload) {
      mergeDraftRows(Array.isArray(payload.items) ? payload.items : [], Number(payload.total || 0));
      renderList();
    });
  }

  function findRenderedRow(rowId) {
    return document.querySelector('[data-row-id="' + rowId + '"]');
  }

  function collectRowData(rowId) {
    var row = findRenderedRow(rowId);
    var payload = {};

    ROW_FIELDS.forEach(function (field) {
      var element = row.querySelector('[data-field="' + field + '"]');
      payload[field] = element ? element.value : "";
    });
    return payload;
  }

  function findDraftRow(rowId) {
    return state.draftRows.find(function (item) {
      return item._draftId === rowId;
    });
  }

  function setEditingRow(rowId) {
    state.editingRowId = rowId || "";
    renderList();
  }

  function saveRow(rowId) {
    var draftItem = findDraftRow(rowId);
    var payload = collectRowData(rowId);
    var method = draftItem ? "POST" : "PUT";
    var url = draftItem ? API_BASE + "/schools" : API_BASE + "/schools/" + encodeURIComponent(rowId);

    setStatus("Salvando escola...", null);
    return fetchJson(url, {
      method: method,
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }).then(function (saved) {
      if (draftItem) {
        state.draftRows = state.draftRows.filter(function (item) {
          return item._draftId !== rowId;
        });
      }
      state.editingRowId = "";
      state.openNotesRowId = "";
      setStatus("Escola salva com sucesso. O mapa local ja pode refletir a mudanca.", "success");
      return loadList().then(function () {
        var savedRow = findRenderedRow(saved.id);
        if (savedRow) {
          savedRow.scrollIntoView({ block: "nearest", inline: "nearest" });
        }
      });
    });
  }

  function cancelEdit(rowId) {
    if (findDraftRow(rowId)) {
      discardDraftRow(rowId);
      return;
    }
    state.editingRowId = "";
    renderList();
    setStatus("Edicao cancelada.", null);
  }

  function discardDraftRow(rowId) {
    state.draftRows = state.draftRows.filter(function (item) {
      return item._draftId !== rowId;
    });
    state.editingRowId = "";
    if (state.openNotesRowId === rowId) {
      state.openNotesRowId = "";
    }
    mergeDraftRows(state.serverItems, state.serverTotal);
    renderList();
    setStatus("Linha descartada.", null);
  }

  function deleteRow(rowId) {
    if (!window.confirm("Excluir esta escola da base unica?")) {
      return Promise.resolve();
    }

    setStatus("Excluindo escola...", null);
    return window
      .fetch(API_BASE + "/schools/" + encodeURIComponent(rowId), {
        method: "DELETE",
      })
      .then(function (response) {
        if (!response.ok) {
          return response.json().then(function (payload) {
            throw new Error(payload.error || "Falha ao excluir escola.");
          });
        }
        return response.json();
      })
      .then(function () {
        state.editingRowId = "";
        if (state.openNotesRowId === rowId) {
          state.openNotesRowId = "";
        }
        setStatus("Escola excluida com sucesso.", "success");
        return loadList();
      });
  }

  function attachScrollSync() {
    var sheet = document.querySelector(".school-sheet");
    var bar = document.getElementById("sheet-scrollbar");

    if (!sheet || !bar) {
      return;
    }

    sheet.addEventListener("scroll", function () {
      if (state.syncingScroll) {
        scheduleOpenNotesPosition();
        return;
      }
      state.syncingScroll = true;
      bar.scrollLeft = sheet.scrollLeft;
      state.syncingScroll = false;
      scheduleOpenNotesPosition();
    });

    bar.addEventListener("scroll", function () {
      if (state.syncingScroll) {
        return;
      }
      state.syncingScroll = true;
      sheet.scrollLeft = bar.scrollLeft;
      state.syncingScroll = false;
      scheduleOpenNotesPosition();
    });

    window.addEventListener("resize", function () {
      window.requestAnimationFrame(function () {
        syncSheetScrollbar();
        positionOpenNotesPopover();
      });
    });

    window.addEventListener(
      "scroll",
      function () {
        scheduleOpenNotesPosition();
      },
      true
    );
  }

  function attachEvents() {
    var searchTimer = null;

    document.getElementById("refresh-button").addEventListener("click", function () {
      loadList().catch(function (error) {
        setStatus(error.message || "Falha ao atualizar a lista.", "danger");
      });
    });

    document.getElementById("search-input").addEventListener("input", function () {
      if (searchTimer) {
        window.clearTimeout(searchTimer);
      }
      searchTimer = window.setTimeout(function () {
        state.page = 0;
        loadList().catch(function (error) {
          setStatus(error.message || "Falha na busca.", "danger");
        });
      }, 180);
    });

    ["network-filter", "municipio-filter"].forEach(function (id) {
      document.getElementById(id).addEventListener("change", function () {
        state.page = 0;
        loadList().catch(function (error) {
          setStatus(error.message || "Falha ao aplicar filtros.", "danger");
        });
      });
    });

    document.getElementById("prev-page-button").addEventListener("click", function () {
      state.page = Math.max(0, state.page - 1);
      loadList().catch(function (error) {
        setStatus(error.message || "Falha ao trocar pagina.", "danger");
      });
    });

    document.getElementById("next-page-button").addEventListener("click", function () {
      state.page += 1;
      loadList().catch(function (error) {
        setStatus(error.message || "Falha ao trocar pagina.", "danger");
      });
    });

    document.getElementById("new-school-button").addEventListener("click", function () {
      if (!state.apiEnabled || state.editingRowId) {
        return;
      }
      var draft = emptySchoolDraft();
      state.draftRows.unshift(draft);
      state.editingRowId = draft._draftId;
      mergeDraftRows(state.serverItems, state.serverTotal);
      renderList();
      setStatus("Nova escola criada em modo de edicao.", null);
    });

    document.getElementById("school-table-body").addEventListener("click", function (event) {
      var trigger = event.target.closest("[data-action][data-row-id]");
      var action;
      var rowId;

      if (!trigger) {
        return;
      }

      action = trigger.getAttribute("data-action");
      rowId = trigger.getAttribute("data-row-id");

      if (action === "edit-row") {
        setEditingRow(rowId);
        setStatus("Edicao ativada para a escola selecionada.", null);
        return;
      }

      if (action === "toggle-notes") {
        state.openNotesRowId = state.openNotesRowId === rowId ? "" : rowId;
        renderList();
        return;
      }

      if (action === "save-row") {
        saveRow(rowId).catch(function (error) {
          setStatus(error.message || "Falha ao salvar escola.", "danger");
        });
        return;
      }

      if (action === "delete-row") {
        deleteRow(rowId).catch(function (error) {
          setStatus(error.message || "Falha ao excluir escola.", "danger");
        });
        return;
      }

      if (action === "discard-row") {
        discardDraftRow(rowId);
        return;
      }

      if (action === "cancel-edit") {
        cancelEdit(rowId);
      }
    });
  }

  function bootstrap() {
    attachEvents();
    attachScrollSync();
    setBaseControlsDisabled(true);
    fetchJson(API_BASE + "/meta")
      .then(function (meta) {
        state.apiEnabled = true;
        state.readOnly = false;
        setModeCopy(
          "Modo completo com API, banco SQLite e sincronizacao automatica para o mapa local."
        );
        setStatus(
          "API conectada. Base unica carregada com " + meta.schoolCount + " escolas.",
          "success"
        );
        return fetchJson(API_BASE + "/options");
      })
      .then(function (options) {
        state.options = options;
        renderOptions();
        setBaseControlsDisabled(false);
        return loadList();
      })
      .catch(function () {
        state.apiEnabled = false;
        state.readOnly = true;
        setModeCopy(
          "Modo leitura para GitHub Pages. A edicao fica disponivel quando a API local estiver ativa."
        );
        setStatus(
          "API nao encontrada. Exibindo os dados publicados do frontend em modo somente leitura.",
          "warn"
        );
        return loadStaticDatasets().then(function () {
          renderOptions();
          setBaseControlsDisabled(false);
          return loadList();
        });
      });
  }

  bootstrap();
})();
