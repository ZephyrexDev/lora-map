"""Tests for the db_session context manager."""

from app.db import db_session
from app.db.models import Tower


class TestDbSession:
    def test_yields_usable_session(self):
        with db_session() as session:
            # Should be able to query without error
            session.query(Tower).all()

    def test_data_persists_across_sessions(self):
        with db_session() as session:
            session.add(Tower(id="cm-t1", name="CM Test", params={"lat": 0, "lon": 0}))
            session.commit()

        with db_session() as session:
            tower = session.get(Tower, "cm-t1")
            assert tower is not None
            assert tower.name == "CM Test"

    def test_rollback_on_no_commit(self):
        with db_session() as session:
            session.add(Tower(id="cm-t2", name="Uncommitted", params={"lat": 0, "lon": 0}))
            # No commit — should be rolled back

        with db_session() as session:
            tower = session.get(Tower, "cm-t2")
            assert tower is None
