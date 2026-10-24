from sqlalchemy import text


def test_sqlite_foreign_keys_are_enforced(db):
    # Guards the PRAGMA listener in app.db.make_engine; several model tests depend on it.
    assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1
