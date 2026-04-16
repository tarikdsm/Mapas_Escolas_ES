from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import scripts.build_density_layer as build_density_layer
import scripts.build_standardized_school_data as build_standardized_school_data
import scripts.build_state_boundary as build_state_boundary


class StandardizedSchoolDataTestCase(unittest.TestCase):
    def test_build_address_combines_unique_parts_only(self) -> None:
        address = build_standardized_school_data.build_address(
            {
                "endereco": "Rua das Flores",
                "numero": "10",
                "complemento": "Bloco A",
                "bairro": "Centro",
            }
        )
        duplicated = build_standardized_school_data.build_address(
            {
                "endereco": "Rua das Flores, Centro",
                "numero": "",
                "complemento": "Centro",
                "bairro": "Centro",
            }
        )

        self.assertEqual(address, "Rua das Flores, 10, Bloco A, Centro")
        self.assertEqual(duplicated, "Rua das Flores, Centro")

    def test_normalize_record_uses_geometry_and_strips_html(self) -> None:
        record = build_standardized_school_data.normalize_record(
            {
                "geometry": {"type": "Point", "coordinates": [-40.3128, -20.3155]},
                "properties": {
                    "nome_escola_padronizado": "<b>Escola Sol</b>",
                    "endereco": "Rua do Sol",
                    "numero": "100",
                    "bairro": "Centro",
                    "municipio": "Vitoria",
                    "cep": "29000-000",
                    "telefone_1": "(27) 3000-0001",
                    "email": "sol@example.com",
                    "numero_professores": "12",
                    "numero_alunos": "300",
                },
            },
            fallback_id="escola-1",
        )

        self.assertEqual(record["Nome_escola"], "Escola Sol")
        self.assertEqual(record["Endereco"], "Rua do Sol, 100, Centro")
        self.assertEqual(record["Latitude"], -20.3155)
        self.assertEqual(record["Longitude"], -40.3128)
        self.assertEqual(record["Numero_professores"], 12)
        self.assertEqual(record["Numero_alunos"], 300)

    def test_build_dataset_orders_records_by_municipio_name_and_address(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.geojson"
            input_path.write_text(
                json.dumps(
                    {
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "geometry": {"type": "Point", "coordinates": [-40.30, -20.31]},
                                "properties": {
                                    "nome_escola": "Escola B",
                                    "municipio": "Serra",
                                    "endereco": "Rua B",
                                },
                            },
                            {
                                "type": "Feature",
                                "geometry": {"type": "Point", "coordinates": [-40.29, -20.30]},
                                "properties": {
                                    "nome_escola": "Escola A",
                                    "municipio": "Cariacica",
                                    "endereco": "Rua A",
                                },
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            records = build_standardized_school_data.build_dataset(input_path)

        self.assertEqual([item["Municipio"] for item in records], ["Cariacica", "Serra"])
        self.assertEqual([item["Nome_escola"] for item in records], ["Escola A", "Escola B"])


class DensityLayerHelpersTestCase(unittest.TestCase):
    def test_parse_indicator_reads_number_and_year_from_ibge_html(self) -> None:
        html = (
            "<section>"
            "<div><p>Area Territorial</p></div>"
            "<p class='ind-value'>1.234,56</p>"
            "<small>Referencia [2022]</small>"
            "</section>"
        )

        value, year = build_density_layer.parse_indicator(html, "Area Territorial")

        self.assertEqual(value, 1234.56)
        self.assertEqual(year, 2022)

    def test_assign_class_and_legend_follow_thresholds(self) -> None:
        self.assertEqual(build_density_layer.assign_class(25.0, [25.0, 50.0, 100.0]), 0)
        self.assertEqual(build_density_layer.assign_class(50.01, [25.0, 50.0, 100.0]), 2)

        legend = build_density_layer.build_legend(build_density_layer.DENSITY_THRESHOLDS)

        self.assertEqual(len(legend), 5)
        self.assertEqual(legend[0]["color"], build_density_layer.COLOR_SCALE[0])
        self.assertEqual(legend[-1]["index"], 4)


class StateBoundaryHelpersTestCase(unittest.TestCase):
    def test_build_outer_rings_reconstructs_external_boundary(self) -> None:
        features = [
            {
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                }
            },
            {
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[1, 0], [2, 0], [2, 1], [1, 1], [1, 0]]],
                }
            },
        ]

        rings = build_state_boundary.build_outer_rings(features)
        feature_collection = build_state_boundary.build_feature_collection(rings)
        geometry = feature_collection["features"][0]["geometry"]

        self.assertEqual(len(rings), 1)
        self.assertEqual(geometry["type"], "Polygon")
        self.assertEqual(rings[0][0], rings[0][-1])
        self.assertGreater(build_state_boundary.ring_area(rings[0]), 0.0)


if __name__ == "__main__":
    unittest.main()
