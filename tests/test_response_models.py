"""Tests for Pydantic response model validation and serialization."""

import pytest
from pydantic import ValidationError

from app.models.DeadzoneResponse import (
    AnalysisBounds,
    DeadzoneAnalysisResponse,
    DeadzoneRegionResponse,
    SiteSuggestionResponse,
)
from app.models.MatrixConfigRequest import MatrixConfigRequest
from app.models.PointToPointResult import PointToPointResult
from app.models.responses import (
    ComputePathsResponse,
    CreatedPathResponse,
    DeleteResponse,
    PredictResponse,
    SimulationResponse,
    TaskStatusResponse,
    TowerLocation,
    TowerPathResponse,
    TowerResponse,
)
from app.models.TowerPathsRequest import TowerPathsRequest


class TestPredictResponse:
    def test_serializes_fields(self):
        r = PredictResponse(task_id="t1", tower_id="tw1")
        assert r.model_dump() == {"task_id": "t1", "tower_id": "tw1"}


class TestTaskStatusResponse:
    def test_error_defaults_to_none(self):
        r = TaskStatusResponse(id="x", status="processing")
        assert r.error is None

    def test_error_included_when_set(self):
        r = TaskStatusResponse(id="x", status="failed", error="boom")
        assert r.error == "boom"


class TestDeleteResponse:
    def test_serializes(self):
        r = DeleteResponse(message="Tower deleted", id="abc")
        d = r.model_dump()
        assert d["message"] == "Tower deleted"
        assert d["id"] == "abc"


class TestTowerResponse:
    def test_color_nullable(self):
        r = TowerResponse(id="x", name="T", color=None, params={}, created_at="now", updated_at="now")
        assert r.color is None

    def test_params_is_dict(self):
        r = TowerResponse(id="x", name="T", color="#ff0000", params={"lat": 1}, created_at="now", updated_at="now")
        assert r.params == {"lat": 1}


class TestTowerLocation:
    def test_fields(self):
        loc = TowerLocation(lat=45.0, lon=-74.0, tx_height=10.0, frequency_mhz=915.0)
        assert loc.lat == 45.0
        assert loc.frequency_mhz == 915.0


class TestSimulationResponse:
    def test_serializes_all_fields(self):
        r = SimulationResponse(
            id="s1",
            client_hardware="v3",
            client_antenna="bingfu_whip",
            terrain_model="bare_earth",
            status="completed",
            created_at="2024-01-01",
        )
        d = r.model_dump()
        assert d["terrain_model"] == "bare_earth"


class TestTowerPathResponse:
    def test_nullable_fields(self):
        r = TowerPathResponse(
            id="p1",
            tower_a_id="a",
            tower_b_id="b",
            lat_a=0,
            lon_a=0,
            lat_b=1,
            lon_b=1,
            path_loss_db=None,
            has_los=None,
            distance_km=None,
            created_at="2024-01-01",
        )
        assert r.path_loss_db is None
        assert r.has_los is None

    def test_populated_fields(self):
        r = TowerPathResponse(
            id="p1",
            tower_a_id="a",
            tower_b_id="b",
            lat_a=45,
            lon_a=-74,
            lat_b=46,
            lon_b=-73,
            path_loss_db=120.5,
            has_los=True,
            distance_km=15.3,
            created_at="2024-01-01",
        )
        assert r.has_los is True
        assert r.distance_km == 15.3


class TestComputePathsResponse:
    def test_count_matches_paths(self):
        paths = [CreatedPathResponse(id="p1", tower_a_id="a", tower_b_id="b")]
        r = ComputePathsResponse(paths=paths, count=1)
        assert len(r.paths) == r.count


class TestPointToPointResult:
    def test_fields(self):
        r = PointToPointResult(path_loss_db=100.0, has_los=True, distance_km=5.0)
        assert r.path_loss_db == 100.0


class TestMatrixConfigRequest:
    def test_accepts_valid_data(self):
        r = MatrixConfigRequest(hardware=["v3"], antennas=["bingfu_whip"], terrain=["bare_earth"])
        assert r.hardware == ["v3"]

    def test_accepts_empty_lists(self):
        r = MatrixConfigRequest(hardware=[], antennas=[], terrain=[])
        assert r.hardware == []

    def test_rejects_missing_fields(self):
        with pytest.raises(ValidationError):
            MatrixConfigRequest(hardware=["v3"])


class TestTowerPathsRequest:
    def test_tower_ids_optional(self):
        r = TowerPathsRequest()
        assert r.tower_ids is None

    def test_tower_ids_accepts_list(self):
        r = TowerPathsRequest(tower_ids=["a", "b"])
        assert r.tower_ids == ["a", "b"]


class TestDeadzoneResponseModels:
    def test_analysis_bounds(self):
        b = AnalysisBounds(north=46.0, south=45.0, east=-73.0, west=-74.0)
        assert b.north > b.south

    def test_site_suggestion_priority_rank_bounds(self):
        s = SiteSuggestionResponse(lat=45.0, lon=-74.0, estimated_coverage_km2=10.0, priority_rank=1, reason="test")
        assert s.priority_rank == 1

    def test_site_suggestion_rejects_rank_zero(self):
        with pytest.raises(ValidationError):
            SiteSuggestionResponse(lat=45.0, lon=-74.0, estimated_coverage_km2=10.0, priority_rank=0, reason="test")

    def test_site_suggestion_rejects_rank_six(self):
        with pytest.raises(ValidationError):
            SiteSuggestionResponse(lat=45.0, lon=-74.0, estimated_coverage_km2=10.0, priority_rank=6, reason="test")

    def test_region_priority_score_bounds(self):
        r = DeadzoneRegionResponse(
            region_id=1,
            center_lat=45.0,
            center_lon=-74.0,
            area_km2=5.0,
            priority_score=0.5,
            pixel_count=100,
        )
        assert 0.0 <= r.priority_score <= 1.0

    def test_region_rejects_negative_priority(self):
        with pytest.raises(ValidationError):
            DeadzoneRegionResponse(
                region_id=1,
                center_lat=45.0,
                center_lon=-74.0,
                area_km2=5.0,
                priority_score=-0.1,
                pixel_count=100,
            )

    def test_region_rejects_priority_above_one(self):
        with pytest.raises(ValidationError):
            DeadzoneRegionResponse(
                region_id=1,
                center_lat=45.0,
                center_lon=-74.0,
                area_km2=5.0,
                priority_score=1.1,
                pixel_count=100,
            )

    def test_full_response_serialization(self):
        resp = DeadzoneAnalysisResponse(
            bounds=AnalysisBounds(north=46, south=45, east=-73, west=-74),
            total_coverage_km2=100.0,
            total_deadzone_km2=50.0,
            coverage_fraction=0.667,
            regions=[],
            suggestions=[],
            tower_count=2,
        )
        d = resp.model_dump()
        assert d["tower_count"] == 2
        assert d["regions"] == []
