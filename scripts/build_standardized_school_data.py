#!/usr/bin/env python3
"""Builds the four standardized school datasets used directly by the frontend."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = FRONTEND_ROOT / "public" / "data" / "schools"

DATASETS = (
    (
        "e_estaduais",
        PROJECT_ROOT
        / "backend"
        / "projects"
        / "escolas_estaduais_es"
        / "data"
        / "frontend_exports"
        / "escolas_estaduais_es_georef.geojson",
    ),
    (
        "e_municipais",
        PROJECT_ROOT
        / "backend"
        / "projects"
        / "escolas_municipais_es"
        / "data"
        / "frontend_exports"
        / "escolas_municipais_es_georef.geojson",
    ),
    (
        "e_federais",
        PROJECT_ROOT
        / "backend"
        / "projects"
        / "escolas_federais_es"
        / "data"
        / "frontend_exports"
        / "escolas_federais_es_georef.geojson",
    ),
    (
        "e_privadas",
        PROJECT_ROOT
        / "backend"
        / "projects"
        / "escolas_particulares_es"
        / "data"
        / "frontend_exports"
        / "escolas_particulares_es_georef.geojson",
    ),
)


def is_nan(value: object) -> bool:
    return isinstance(value, float) and math.isnan(value)


def clean_text(value: object) -> str:
    if value is None or is_nan(value):
        return ""
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    return text


def clean_html_text(value: object) -> str:
    text = clean_text(value)
    if not text:
        return ""
    return clean_text(re.sub(r"<[^>]+>", " ", text))


def first_text(properties: dict[str, object], *keys: str) -> str:
    for key in keys:
        text = clean_text(properties.get(key))
        if text:
            return text
    return ""


def first_number(properties: dict[str, object], *keys: str) -> int | None:
    for key in keys:
        value = properties.get(key)
        if value is None or is_nan(value):
            continue
        text = clean_text(value)
        if not text:
            continue
        try:
            return int(round(float(text.replace(",", "."))))
        except ValueError:
            continue
    return None


def sanitize_geometry_number(value: object) -> float | None:
    if value is None or is_nan(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def contains_text(base_text: str, candidate: str) -> bool:
    if not base_text or not candidate:
        return False
    return candidate.casefold() in base_text.casefold()


def build_address(properties: dict[str, object]) -> str:
    address = first_text(properties, "endereco", "address")
    extras = []

    for keys in (
        ("numero", "number"),
        ("complemento", "complement"),
        ("bairro", "district"),
    ):
        extra = first_text(properties, *keys)
        if extra and not contains_text(address, extra):
            extras.append(extra)

    return ", ".join([part for part in [address] + extras if part])


def normalize_record(feature: dict[str, object], fallback_id: str) -> dict[str, object] | None:
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates") or []
    properties = feature.get("properties") or {}

    if geometry.get("type") != "Point" or len(coordinates) != 2:
        return None

    longitude = sanitize_geometry_number(coordinates[0])
    latitude = sanitize_geometry_number(coordinates[1])
    if longitude is None or latitude is None:
        longitude = sanitize_geometry_number(properties.get("longitude"))
        latitude = sanitize_geometry_number(properties.get("latitude"))
    if longitude is None or latitude is None:
        return None

    school_name = (
        clean_html_text(
            properties.get("nome_escola_padronizado")
            or properties.get("nome_escola_original")
            or properties.get("nome_escola")
            or properties.get("name")
        )
        or fallback_id
    )

    return {
        "Nome_escola": school_name,
        "Endereco": build_address(properties),
        "Municipio": first_text(properties, "municipio"),
        "CEP": first_text(properties, "cep", "postal_code"),
        "telefone": first_text(properties, "telefone_1", "telefone", "phone_primary", "phone"),
        "email": first_text(properties, "email"),
        "Latitude": round(latitude, 6),
        "Longitude": round(longitude, 6),
        "Numero_professores": first_number(properties, "numero_professores", "teacher_count"),
        "Numero_alunos": first_number(properties, "numero_alunos", "student_count"),
    }


def load_geojson(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_dataset(input_path: Path) -> list[dict[str, object]]:
    source = load_geojson(input_path)
    records = []

    for index, feature in enumerate(source.get("features", []), start=1):
        record = normalize_record(feature, fallback_id=f"escola-{index}")
        if record is not None:
            records.append(record)

    records.sort(
        key=lambda item: (
            item["Municipio"] or "",
            item["Nome_escola"] or "",
            item["Endereco"] or "",
        )
    )
    return records


def write_dataset(output_path: Path, records: list[dict[str, object]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    print("Generating standardized frontend datasets...")
    for dataset_name, input_path in DATASETS:
        if not input_path.exists():
            raise FileNotFoundError(f"Input dataset not found: {input_path}")

        records = build_dataset(input_path)
        output_path = OUTPUT_DIR / f"{dataset_name}.json"
        write_dataset(output_path, records)
        print(f"- {dataset_name}: {len(records)} schools -> {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
