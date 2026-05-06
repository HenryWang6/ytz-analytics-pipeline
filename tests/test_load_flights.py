import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from load_flights import get_pending_files, SnowflakeLoader


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
