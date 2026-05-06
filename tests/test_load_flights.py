import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from load_flights import get_pending_files, SnowflakeLoader, _extract_direction


class TestExtractDirection:
    def test_parses_departure(self):
        assert _extract_direction("flights_departure_20260430_171743.json") == "DEPARTURE"

    def test_parses_arrival(self):
        assert _extract_direction("flights_arrival_20260430_171746.json") == "ARRIVAL"

    def test_returns_unknown_for_malformed(self):
        assert _extract_direction("bad_filename.json") == "UNKNOWN"

    def test_returns_unknown_for_wrong_pattern(self):
        assert _extract_direction("flights_unknown_20260430_171746.json") == "UNKNOWN"


class TestGetPendingFiles:
    def test_returns_empty_list_for_missing_dir(self):
        result = get_pending_files("/nonexistent/path")
        assert result == []

    def test_finds_json_files(self, tmp_path):
        (tmp_path / "file_a.json").write_text("{}")
        (tmp_path / "file_b.json").write_text("{}")
        (tmp_path / "not_json.txt").write_text("text")
        files = get_pending_files(str(tmp_path))
        assert len(files) == 2
        assert all(f.endswith(".json") for f in files)

    def test_ignores_archive_subdirectory(self, tmp_path):
        archive = tmp_path / "archive"
        archive.mkdir()
        (archive / "old_file.json").write_text("{}")
        (tmp_path / "new_file.json").write_text("{}")
        files = get_pending_files(str(tmp_path))
        assert len(files) == 1
        assert "new_file.json" in files[0]


class TestSnowflakeLoader:
    def test_init_stores_connection_params(self):
        loader = SnowflakeLoader(
            account="test_account",
            user="test_user",
            password="test_pass",
            role="ANALYST",
            warehouse="MY_WH",
            database="TEST_DB",
            schema="PUBLIC",
        )
        assert loader.account == "test_account"
        assert loader.user == "test_user"
        assert loader.role == "ANALYST"
        assert loader.warehouse == "MY_WH"
