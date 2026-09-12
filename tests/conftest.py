import pytest
from lottolab.db import Base, make_engine, make_session_factory


@pytest.fixture
def session_factory(tmp_path):
    engine = make_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    yield factory
    engine.dispose()


@pytest.fixture
def raw_draw():
    return {
        "lottery": "ssq",
        "issue": "2026105",
        "draw_date": "2026-09-10",
        "main_numbers": [2, 4, 13, 14, 15, 30],
        "special_numbers": [8],
    }
