"""Tests for shared helper functions in app.main."""

from uuid import uuid4

import pytest

from app.db import db_session
from app.db.models import Tower
from app.models.responses import TowerLocation
from tests.conftest import insert_tower

pytestmark = pytest.mark.slow


class TestGetTowerLocation:
    def test_returns_location_for_existing_tower(self, client):
        from app.main import _get_tower_location

        tid = str(uuid4())
        with db_session() as session:
            session.add(
                Tower(
                    id=tid,
                    name="T",
                    params={"lat": 45.5, "lon": -74.2, "tx_height": 10, "frequency_mhz": 915},
                )
            )
            session.commit()
            loc = _get_tower_location(session, tid)

        assert isinstance(loc, TowerLocation)
        assert loc.lat == 45.5
        assert loc.lon == -74.2
        assert loc.tx_height == 10
        assert loc.frequency_mhz == 915

    def test_returns_none_for_missing_tower(self, client):
        from app.main import _get_tower_location

        with db_session() as session:
            loc = _get_tower_location(session, str(uuid4()))
        assert loc is None

    def test_raises_for_missing_required_fields(self, client):
        from app.main import _get_tower_location

        tid = str(uuid4())
        with db_session() as session:
            session.add(Tower(id=tid, name="T", params={}))
            session.commit()
            with pytest.raises(ValueError, match="missing required param"):
                _get_tower_location(session, tid)


class TestGeotiffResponseOrStatus:
    def test_returns_streaming_for_completed(self, client):
        from fastapi.responses import StreamingResponse

        from app.main import _geotiff_response_or_status

        resp = _geotiff_response_or_status("completed", b"TIFF_DATA", None, "test-id")
        assert isinstance(resp, StreamingResponse)

    def test_raises_500_for_completed_with_no_data(self, client):
        from fastapi import HTTPException

        from app.main import _geotiff_response_or_status

        with pytest.raises(HTTPException) as exc_info:
            _geotiff_response_or_status("completed", None, None, "test-id")
        assert exc_info.value.status_code == 500

    def test_returns_status_for_processing(self, client):
        from app.main import _geotiff_response_or_status
        from app.models.responses import TaskStatusResponse

        resp = _geotiff_response_or_status("processing", None, None, "test-id")
        assert isinstance(resp, TaskStatusResponse)
        assert resp.status == "processing"
        assert resp.error is None

    def test_returns_error_for_failed(self, client):
        from app.main import _geotiff_response_or_status
        from app.models.responses import TaskStatusResponse

        resp = _geotiff_response_or_status("failed", None, "crash", "test-id")
        assert isinstance(resp, TaskStatusResponse)
        assert resp.status == "failed"
        assert resp.error == "crash"


class TestDeleteRow:
    def test_raises_404_for_nonexistent(self, client):
        from fastapi import HTTPException

        from app.main import _delete_row

        with pytest.raises(HTTPException) as exc_info:
            _delete_row(Tower, str(uuid4()), "Tower")
        assert exc_info.value.status_code == 404

    def test_returns_delete_response_on_success(self, client):
        from app.main import _delete_row
        from app.models.responses import DeleteResponse

        tid = insert_tower()
        result = _delete_row(Tower, tid, "Tower")
        assert isinstance(result, DeleteResponse)
        assert result.id == tid
