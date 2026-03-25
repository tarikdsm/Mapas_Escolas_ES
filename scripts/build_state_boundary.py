#!/usr/bin/env python3
"""Build a more faithful ES state boundary from official municipal polygons."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

Coordinate = Tuple[float, float]


def point_key(point: Sequence[float]) -> str:
    return f"{point[0]:.10f},{point[1]:.10f}"


def edge_key(start: Sequence[float], end: Sequence[float]) -> str:
    a = point_key(start)
    b = point_key(end)
    return f"{a}|{b}" if a < b else f"{b}|{a}"


def iter_exterior_rings(feature: dict) -> Iterable[List[Sequence[float]]]:
    geometry = feature.get("geometry") or {}
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates") or []

    if geometry_type == "Polygon":
        if coordinates:
            yield coordinates[0]
        return

    if geometry_type == "MultiPolygon":
        for polygon in coordinates:
            if polygon:
                yield polygon[0]


def build_outer_rings(features: Sequence[dict]) -> List[List[Coordinate]]:
    edge_counts: Dict[str, int] = defaultdict(int)
    directed_edges = []

    for feature in features:
        for ring in iter_exterior_rings(feature):
            for index in range(len(ring) - 1):
                start = tuple(ring[index])
                end = tuple(ring[index + 1])
                key = edge_key(start, end)
                edge_counts[key] += 1
                directed_edges.append((tuple(start), tuple(end), key))

    adjacency: Dict[str, List[str]] = defaultdict(list)
    coordinates_by_key: Dict[str, Coordinate] = {}

    for start, end, key in directed_edges:
        if edge_counts[key] != 1:
            continue

        start_key = point_key(start)
        end_key = point_key(end)
        coordinates_by_key[start_key] = start
        coordinates_by_key[end_key] = end
        adjacency[start_key].append(end_key)
        adjacency[end_key].append(start_key)

    visited_edges = set()
    rings: List[List[Coordinate]] = []

    for start_key, neighbors in adjacency.items():
        for neighbor_key in neighbors:
            current_edge = (
                f"{start_key}|{neighbor_key}"
                if start_key < neighbor_key
                else f"{neighbor_key}|{start_key}"
            )
            if current_edge in visited_edges:
                continue

            ring: List[Coordinate] = [coordinates_by_key[start_key]]
            previous_key = start_key
            current_key = neighbor_key
            visited_edges.add(current_edge)
            ring.append(coordinates_by_key[current_key])

            while current_key != start_key:
                next_options = [
                    item for item in adjacency[current_key] if item != previous_key
                ]
                if not next_options:
                    break

                next_key = None
                for option in next_options:
                    option_edge = (
                        f"{current_key}|{option}"
                        if current_key < option
                        else f"{option}|{current_key}"
                    )
                    if option == start_key or option_edge not in visited_edges:
                        next_key = option
                        visited_edges.add(option_edge)
                        break

                if next_key is None:
                    break

                previous_key, current_key = current_key, next_key
                ring.append(coordinates_by_key[current_key])

                if len(ring) > 20000:
                    raise RuntimeError("Boundary reconstruction exceeded safe loop size.")

            if len(ring) > 3 and ring[0] == ring[-1]:
                rings.append(ring)

    if not rings:
        raise RuntimeError("No exterior rings were reconstructed from municipal polygons.")

    return rings


def ring_area(ring: Sequence[Coordinate]) -> float:
    area = 0.0
    for index in range(len(ring) - 1):
        x1, y1 = ring[index]
        x2, y2 = ring[index + 1]
        area += (x1 * y2) - (x2 * y1)
    return abs(area / 2.0)


def build_feature_collection(rings: Sequence[Sequence[Coordinate]]) -> dict:
    ordered_rings = sorted(rings, key=ring_area, reverse=True)

    if len(ordered_rings) == 1:
        geometry = {
            "type": "Polygon",
            "coordinates": [[list(point) for point in ordered_rings[0]]],
        }
    else:
        geometry = {
            "type": "MultiPolygon",
            "coordinates": [
                [[list(point) for point in ring]] for ring in ordered_rings
            ],
        }

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "codarea": "32",
                    "source": "IBGE municipal polygons",
                    "derivation": "outer boundary of ES municipalities",
                },
            }
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build ES state boundary from municipal GeoJSON."
    )
    parser.add_argument("--input", required=True, help="Municipal GeoJSON input path.")
    parser.add_argument("--output", required=True, help="State GeoJSON output path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    features = payload.get("features") or []
    rings = build_outer_rings(features)
    feature_collection = build_feature_collection(rings)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(feature_collection, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
