#!/usr/bin/env python3
"""Gera a camada de densidade demográfica municipal do ES a partir de dados oficiais do IBGE."""

from __future__ import annotations

import argparse
import gzip
import html
import json
import re
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


UF = "es"
MUNICIPALITIES_URL = (
    "https://servicodados.ibge.gov.br/api/v1/localidades/estados/32/municipios"
)
MUNICIPALITIES_GEOJSON_URL = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/estados/ES"
    "?intrarregiao=municipio&formato=application/vnd.geo+json&qualidade=minima"
)

COLOR_SCALE = ["#fff3d4", "#fdcf86", "#f79b4d", "#db6d30", "#9f3c1f"]
DENSITY_THRESHOLDS = [25.0, 50.0, 100.0, 500.0]


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "mapas-escolas-es/1.0",
            "Accept-Encoding": "gzip",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
    return data.decode("utf-8", errors="replace")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", without_accents.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def parse_brazilian_number(value: str) -> float:
    cleaned = value.replace(".", "").replace(",", ".").strip()
    return float(cleaned)


def parse_indicator(page_html: str, label: str) -> tuple[float, int | None]:
    decoded = html.unescape(page_html)
    pattern = re.compile(
        rf"<p>{re.escape(label)}</p></div><p class='ind-value'>([^<]+).*?<small>.*?\[(\d{{4}})\]</small>",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(decoded)
    if not match:
        raise ValueError(f"Indicador não encontrado: {label}")
    return parse_brazilian_number(match.group(1).strip()), int(match.group(2))


def fetch_municipality_metrics(uf: str, municipality_name: str) -> dict[str, object]:
    url = f"https://www.ibge.gov.br/cidades-e-estados/{uf}/{slugify(municipality_name)}.html"
    page_html = fetch_text(url)
    area, area_year = parse_indicator(page_html, "Área Territorial")
    population, population_year = parse_indicator(page_html, "População no último censo")
    density, density_year = parse_indicator(page_html, "Densidade demográfica")
    return {
        "municipio_nome": municipality_name,
        "area_territorial_km2": area,
        "area_territorial_ano": area_year,
        "populacao_censo_2022": int(round(population)),
        "populacao_censo_ano": population_year,
        "densidade_demografica": density,
        "densidade_ano": density_year,
        "ibge_url": url,
    }


def assign_class(value: float, thresholds: list[float]) -> int:
    for index, upper in enumerate(thresholds):
        if value <= upper:
            return index
    return len(thresholds)


def build_legend(thresholds: list[float]) -> list[dict[str, object]]:
    labels = [
        "Até 25,00 hab/km²",
        "25,01 a 50,00 hab/km²",
        "50,01 a 100,00 hab/km²",
        "100,01 a 500,00 hab/km²",
        "Acima de 500,00 hab/km²",
    ]
    return [
        {"index": index, "label": labels[index], "color": COLOR_SCALE[index]}
        for index in range(len(labels))
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        required=True,
        help="Arquivo GeoJSON de saída.",
    )
    args = parser.parse_args()

    municipalities = json.loads(fetch_text(MUNICIPALITIES_URL))
    municipalities_geojson = json.loads(fetch_text(MUNICIPALITIES_GEOJSON_URL))

    metrics_by_code = {}
    for municipality in municipalities:
        metrics = fetch_municipality_metrics(UF, municipality["nome"])
        metrics_by_code[str(municipality["id"])] = metrics
        print(f"IBGE: {municipality['nome']}")

    legend = build_legend(DENSITY_THRESHOLDS)

    for feature in municipalities_geojson.get("features", []):
        code = str(feature["properties"]["codarea"])
        metrics = metrics_by_code[code]
        density = float(metrics["densidade_demografica"])
        density_class = assign_class(density, DENSITY_THRESHOLDS)
        feature["properties"] = {
            "municipio_id": code,
            "municipio_nome": metrics["municipio_nome"],
            "area_territorial_km2": metrics["area_territorial_km2"],
            "area_territorial_ano": metrics["area_territorial_ano"],
            "populacao_censo_2022": metrics["populacao_censo_2022"],
            "populacao_censo_ano": metrics["populacao_censo_ano"],
            "densidade_demografica": metrics["densidade_demografica"],
            "densidade_ano": metrics["densidade_ano"],
            "density_class": density_class,
            "density_class_label": legend[density_class]["label"],
            "ibge_url": metrics["ibge_url"],
        }

    municipalities_geojson["metadata"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "uf": "ES",
        "state_name": "Espírito Santo",
        "legend": legend,
        "source_note": (
            "IBGE Cidades e Estados para densidade demográfica e população do Censo 2022; "
            "API de Malhas do IBGE para os polígonos municipais."
        ),
        "sources": {
            "municipalities_api": MUNICIPALITIES_URL,
            "boundaries_api": MUNICIPALITIES_GEOJSON_URL,
            "cidades_e_estados_root": "https://www.ibge.gov.br/cidades-e-estados/es/"
        }
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(municipalities_geojson, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Camada de densidade gerada em: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
