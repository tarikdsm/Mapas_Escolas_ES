#!/usr/bin/env python3
"""Normaliza uma base GeoJSON de escolas para consumo do site."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


OUTPUT_FIELDS = {
    "id_interno": "id",
    "codigo_inep": "inep_code",
    "nome_escola": "name",
    "municipio": "municipio",
    "uf": "uf",
    "dependencia_administrativa": "administrative_dependency",
    "situacao_funcionamento": "status",
    "tipo_localizacao": "location_type",
    "endereco": "address",
    "numero": "number",
    "bairro": "district",
    "cep": "postal_code",
    "telefone_1": "phone_primary",
    "telefone_2": "phone_secondary",
    "email": "email",
    "classificacao_georef": "classification",
    "criterio_georef": "georef_criterion",
    "fonte_georef": "georef_source",
    "fonte_principal": "source_primary",
    "fonte_validacao": "source_validation",
    "latitude": "latitude",
    "longitude": "longitude",
}


def clean_bom_key(properties: dict[str, object]) -> dict[str, object]:
    cleaned = {}
    for key, value in properties.items():
        normalized_key = key.lstrip("\ufeff").replace("ï»¿", "")
        cleaned[normalized_key] = value
    return cleaned


def normalize_feature(
    feature: dict[str, object],
    layer_id: str,
    layer_label: str,
    color: str,
) -> dict[str, object] | None:
    geometry = feature.get("geometry")
    if not geometry or geometry.get("type") != "Point":
        return None

    properties = clean_bom_key(feature.get("properties", {}))
    coordinates = geometry.get("coordinates", [])
    if len(coordinates) != 2:
        return None

    output_properties = {
        target_key: properties.get(source_key, "")
        for source_key, target_key in OUTPUT_FIELDS.items()
    }
    output_properties.update(
        {
            "layer_id": layer_id,
            "layer_label": layer_label,
            "layer_color": color,
        }
    )

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [float(coordinates[0]), float(coordinates[1])],
        },
        "properties": output_properties,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Caminho do GeoJSON de origem.")
    parser.add_argument("--output", required=True, help="Caminho do GeoJSON de saída.")
    parser.add_argument("--layer-id", required=True, help="ID da camada.")
    parser.add_argument("--label", required=True, help="Rótulo da camada.")
    parser.add_argument("--color", required=True, help="Cor da camada em HEX.")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    source = json.loads(input_path.read_text(encoding="utf-8-sig"))

    features = []
    for feature in source.get("features", []):
        normalized = normalize_feature(feature, args.layer_id, args.label, args.color)
        if normalized is not None:
            features.append(normalized)

    features.sort(
        key=lambda item: (
            str(item["properties"].get("municipio", "")),
            str(item["properties"].get("name", "")),
            str(item["properties"].get("inep_code", "")),
        )
    )

    payload = {
        "type": "FeatureCollection",
        "metadata": {
            "layer_id": args.layer_id,
            "label": args.label,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_features": len(features),
            "source_path": str(input_path),
        },
        "features": features,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Camada gerada: {output_path}")
    print(f"Total de registros: {len(features)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

