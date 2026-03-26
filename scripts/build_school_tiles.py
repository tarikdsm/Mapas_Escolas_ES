#!/usr/bin/env python3
"""Gera tiles clusterizados e shards de detalhe para as camadas escolares."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


TILE_SIZE = 256
MAX_MERCATOR_LAT = 85.05112878


@dataclass(frozen=True)
class SchoolRecord:
    school_id: str
    inep_code: str
    name: str
    municipio: str
    detail_shard: str
    longitude: float
    latitude: float
    teacher_count: int | None
    detail: dict[str, object]


def teacher_bucket(value: int | None) -> int:
    if value is None:
        return 0
    return max(0, int(value))


def build_teacher_histogram(schools: list[SchoolRecord]) -> list[list[int]]:
    histogram: dict[int, int] = defaultdict(int)
    for school in schools:
        histogram[teacher_bucket(school.teacher_count)] += 1
    return [[bucket, histogram[bucket]] for bucket in sorted(histogram)]


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    return text


def first_text(properties: dict[str, object], *keys: str) -> str:
    for key in keys:
        text = clean_text(properties.get(key))
        if text:
            return text
    return ""


def strip_html(value: object) -> str:
    text = clean_text(value)
    if not text:
        return ""
    return clean_text(re.sub(r"<[^>]+>", " ", text))


def clean_int(value: object) -> int | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        return int(round(float(text)))
    except ValueError:
        return None


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", clean_text(value))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    parts = ["".join(character for character in chunk if character.isalnum()) for chunk in ascii_text.split()]
    filtered = [chunk for chunk in parts if chunk]
    return "-".join(filtered) or "sem-municipio"


def clamp_latitude(latitude: float) -> float:
    return max(-MAX_MERCATOR_LAT, min(MAX_MERCATOR_LAT, latitude))


def project(longitude: float, latitude: float, zoom: int) -> tuple[float, float]:
    latitude = clamp_latitude(latitude)
    scale = (2**zoom) * TILE_SIZE
    siny = math.sin(math.radians(latitude))
    x = (longitude + 180.0) / 360.0 * scale
    y = (0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi)) * scale
    return x, y


def tile_indices(longitude: float, latitude: float, zoom: int) -> tuple[int, int]:
    pixel_x, pixel_y = project(longitude, latitude, zoom)
    limit = (2**zoom) - 1
    tile_x = max(0, min(limit, int(pixel_x // TILE_SIZE)))
    tile_y = max(0, min(limit, int(pixel_y // TILE_SIZE)))
    return tile_x, tile_y


def compact_dict(payload: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in payload.items()
        if value not in ("", None, [], {})
    }


def build_address_line(properties: dict[str, object]) -> str:
    parts = [
        ", ".join(
            item
            for item in [
                clean_text(properties.get("address")),
                clean_text(properties.get("number")),
            ]
            if item
        ),
        clean_text(properties.get("district")),
        clean_text(properties.get("municipio")),
        clean_text(properties.get("uf")),
        clean_text(properties.get("postal_code")),
    ]
    return " · ".join(part for part in parts if part)


def build_georef_label(properties: dict[str, object]) -> str:
    parts = [
        clean_text(properties.get("classification")),
        clean_text(properties.get("georef_source")),
    ]
    return " · ".join(part for part in parts if part)


def load_features(input_path: Path) -> list[SchoolRecord]:
    source = json.loads(input_path.read_text(encoding="utf-8"))
    features = []

    for index, feature in enumerate(source.get("features", []), start=1):
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if geometry.get("type") != "Point" or len(coordinates) != 2:
            continue

        properties = feature.get("properties") or {}
        school_id = first_text(
            properties,
            "id_interno",
            "id",
            "codigo_inep",
            "inep_code",
            "codigo_escola",
        ) or f"school-{index}"
        inep_code = first_text(properties, "codigo_inep", "inep_code", "codigo_escola")
        name = (
            first_text(
                properties,
                "nome_escola_original",
                "name_original",
                "nome_escola_padronizado",
                "nome_escola",
                "name",
            )
            or strip_html(properties.get("nome_escola_mapa_html"))
            or school_id
        )
        municipio = clean_text(properties.get("municipio"))
        detail_shard = slugify(municipio)
        longitude = float(coordinates[0])
        latitude = float(coordinates[1])
        teacher_count = clean_int(
            properties.get("numero_professores")
            if properties.get("numero_professores") is not None
            else properties.get("teacher_count")
        )

        detail = compact_dict(
            {
                "id": school_id,
                "inep_code": inep_code,
                "name": name,
                "name_original": first_text(
                    properties,
                    "nome_escola_original",
                    "name_original",
                    "nome_escola",
                    "name",
                )
                or name,
                "municipio": municipio,
                "uf": clean_text(properties.get("uf")),
                "status": first_text(properties, "situacao_funcionamento", "status"),
                "address": first_text(properties, "endereco", "address"),
                "number": first_text(properties, "numero", "number"),
                "complement": first_text(properties, "complemento", "complement"),
                "district": first_text(properties, "bairro", "district"),
                "postal_code": first_text(properties, "cep", "postal_code"),
                "classification": first_text(
                    properties,
                    "classificacao_georef",
                    "classification",
                ),
                "georef_source": first_text(properties, "fonte_georef", "georef_source"),
                "phone_primary": first_text(properties, "telefone_1", "phone_primary"),
                "email": clean_text(properties.get("email")),
                "teacher_count": teacher_count,
            }
        )

        features.append(
            SchoolRecord(
                school_id=school_id,
                inep_code=inep_code,
                name=name,
                municipio=municipio,
                detail_shard=detail_shard,
                longitude=longitude,
                latitude=latitude,
                teacher_count=teacher_count,
                detail=detail,
            )
        )

    features.sort(key=lambda item: (item.municipio, item.name, item.inep_code, item.school_id))
    return features


def build_tile_payloads(
    schools: list[SchoolRecord],
    min_zoom: int,
    max_zoom: int,
    cluster_max_zoom: int,
    cluster_radius_px: int,
) -> dict[tuple[int, int, int], list[dict[str, object]]]:
    tile_payloads: dict[tuple[int, int, int], list[dict[str, object]]] = defaultdict(list)

    for zoom in range(min_zoom, max_zoom + 1):
        if zoom > cluster_max_zoom:
            for school in schools:
                tile_key = (zoom,) + tile_indices(school.longitude, school.latitude, zoom)
                tile_payloads[tile_key].append(
                    compact_dict(
                        {
                            "k": "s",
                            "i": school.school_id,
                            "x": round(school.longitude, 6),
                            "y": round(school.latitude, 6),
                            "n": school.name,
                            "t": school.teacher_count,
                            "d": school.detail_shard,
                        }
                    )
                )
            continue

        grouped: dict[tuple[int, int], list[SchoolRecord]] = defaultdict(list)
        for school in schools:
            pixel_x, pixel_y = project(school.longitude, school.latitude, zoom)
            grouped[(int(pixel_x // cluster_radius_px), int(pixel_y // cluster_radius_px))].append(school)

        for grid_key, grouped_schools in grouped.items():
            if len(grouped_schools) == 1:
                school = grouped_schools[0]
                tile_key = (zoom,) + tile_indices(school.longitude, school.latitude, zoom)
                tile_payloads[tile_key].append(
                    compact_dict(
                        {
                            "k": "s",
                            "i": school.school_id,
                            "x": round(school.longitude, 6),
                            "y": round(school.latitude, 6),
                            "n": school.name,
                            "t": school.teacher_count,
                            "d": school.detail_shard,
                        }
                    )
                )
                continue

            longitude = sum(item.longitude for item in grouped_schools) / len(grouped_schools)
            latitude = sum(item.latitude for item in grouped_schools) / len(grouped_schools)
            bbox = [
                round(min(item.longitude for item in grouped_schools), 6),
                round(min(item.latitude for item in grouped_schools), 6),
                round(max(item.longitude for item in grouped_schools), 6),
                round(max(item.latitude for item in grouped_schools), 6),
            ]
            cluster_id = f"c-{zoom}-{grid_key[0]}-{grid_key[1]}"
            tile_key = (zoom,) + tile_indices(longitude, latitude, zoom)
            tile_payloads[tile_key].append(
                {
                    "k": "c",
                    "i": cluster_id,
                    "x": round(longitude, 6),
                    "y": round(latitude, 6),
                    "p": len(grouped_schools),
                    "b": bbox,
                    "h": build_teacher_histogram(grouped_schools),
                }
            )

    for payload in tile_payloads.values():
        payload.sort(key=lambda item: (item.get("k"), item.get("i")))

    return tile_payloads


def write_tile_payloads(
    output_dir: Path,
    payloads: dict[tuple[int, int, int], list[dict[str, object]]],
) -> tuple[dict[int, int], list[str]]:
    tiles_dir = output_dir / "tiles"
    if tiles_dir.exists():
        shutil.rmtree(tiles_dir)
    tiles_dir.mkdir(parents=True, exist_ok=True)

    zoom_counts: dict[int, int] = defaultdict(int)
    tile_keys: list[str] = []
    for (zoom, tile_x, tile_y), features in payloads.items():
        tile_path = tiles_dir / str(zoom) / str(tile_x) / f"{tile_y}.json"
        tile_path.parent.mkdir(parents=True, exist_ok=True)
        tile_path.write_text(
            json.dumps({"z": zoom, "x": tile_x, "y": tile_y, "features": features}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        zoom_counts[zoom] += 1
        tile_keys.append(f"{zoom}:{tile_x}:{tile_y}")

    tile_keys.sort()
    return dict(sorted(zoom_counts.items())), tile_keys


def write_detail_shards(output_dir: Path, schools: list[SchoolRecord]) -> dict[str, int]:
    details_dir = output_dir / "details"
    if details_dir.exists():
        shutil.rmtree(details_dir)
    details_dir.mkdir(parents=True, exist_ok=True)

    grouped: dict[str, list[SchoolRecord]] = defaultdict(list)
    for school in schools:
        grouped[school.detail_shard].append(school)

    shard_sizes: dict[str, int] = {}
    for shard_key, shard_schools in sorted(grouped.items()):
        payload = {
            "shard": shard_key,
            "schools": {
                school.school_id: school.detail
                for school in shard_schools
            },
        }
        detail_path = details_dir / f"{shard_key}.json"
        detail_path.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        shard_sizes[shard_key] = len(shard_schools)

    return shard_sizes


def compute_bounds(schools: list[SchoolRecord]) -> list[float]:
    return [
        round(min(item.longitude for item in schools), 6),
        round(min(item.latitude for item in schools), 6),
        round(max(item.longitude for item in schools), 6),
        round(max(item.latitude for item in schools), 6),
    ]


def build_manifest(
    schools: list[SchoolRecord],
    args: argparse.Namespace,
    tile_counts_by_zoom: dict[int, int],
    tile_keys: list[str],
    detail_shards: dict[str, int],
) -> dict[str, object]:
    teacher_histogram = build_teacher_histogram(schools)
    return {
        "layerId": args.layer_id,
        "label": args.label,
        "color": args.color,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "schoolCount": len(schools),
        "bounds": compute_bounds(schools),
        "tiles": {
            "pathTemplate": "tiles/{z}/{x}/{y}.json",
            "minZoom": args.min_zoom,
            "maxZoom": args.max_zoom,
            "clusterMaxZoom": args.cluster_max_zoom,
            "clusterRadiusPx": args.cluster_radius_px,
            "bufferTiles": args.buffer_tiles,
            "countsByZoom": tile_counts_by_zoom,
            "availableKeys": tile_keys,
            "schema": {
                "school": {"k": "s", "i": "id", "x": "longitude", "y": "latitude", "n": "name", "t": "teacher_count", "d": "detail_shard"},
                "cluster": {"k": "c", "i": "id", "x": "longitude", "y": "latitude", "p": "point_count", "b": "bbox", "h": "teacher_histogram"},
            },
        },
        "details": {
            "pathTemplate": "details/{shard}.json",
            "shardStrategy": "municipio",
            "shardCount": len(detail_shards),
        },
        "filter": {
            "teacherHistogram": teacher_histogram,
            "maxTeacherCount": max((bucket for bucket, _ in teacher_histogram), default=0),
        },
        "source": {
            "input": str(args.input),
        },
        "performance": {
            "contract": "slim_tiles_with_lazy_details",
            "discardOffscreenTiles": True,
            "popupHydration": "on_demand",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="GeoJSON de origem com propriedades detalhadas.")
    parser.add_argument("--output-dir", required=True, help="Diretório de saída da camada otimizada.")
    parser.add_argument("--layer-id", required=True, help="ID da camada.")
    parser.add_argument("--label", required=True, help="Rótulo amigável da camada.")
    parser.add_argument("--color", required=True, help="Cor principal da camada.")
    parser.add_argument("--min-zoom", type=int, default=7, help="Zoom mínimo dos tiles.")
    parser.add_argument("--max-zoom", type=int, default=18, help="Zoom máximo dos tiles.")
    parser.add_argument("--cluster-max-zoom", type=int, default=14, help="Último zoom com clusters pré-computados.")
    parser.add_argument("--cluster-radius-px", type=int, default=64, help="Raio em pixels da grade de clusterização.")
    parser.add_argument("--buffer-tiles", type=int, default=1, help="Quantidade de tiles de margem carregados além do viewport.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    schools = load_features(input_path)
    payloads = build_tile_payloads(
        schools=schools,
        min_zoom=args.min_zoom,
        max_zoom=args.max_zoom,
        cluster_max_zoom=args.cluster_max_zoom,
        cluster_radius_px=args.cluster_radius_px,
    )
    tile_counts_by_zoom, tile_keys = write_tile_payloads(output_dir, payloads)
    detail_shards = write_detail_shards(output_dir, schools)
    manifest = build_manifest(schools, args, tile_counts_by_zoom, tile_keys, detail_shards)
    (output_dir / "index.json").write_text(
        json.dumps(manifest, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    print(f"Camada otimizada gerada em: {output_dir}")
    print(f"Escolas: {len(schools)}")
    print(f"Tiles: {sum(tile_counts_by_zoom.values())}")
    print(f"Shards de detalhe: {len(detail_shards)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
