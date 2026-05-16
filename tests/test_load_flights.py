import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from load_flights import get_pending_files, SnowflakeLoader, _parse_filename, main


class TestParseFilename:
    def test_parses_departure_with_timestamp(self):
        direction, extracted_at = _parse_filename("flights_departure_20260430_171743.json")
        assert direction == "DEPARTURE"
        assert extracted_at == "'2026-04-30 17:17:43'"

    def test_parses_arrival_with_timestamp(self):
        direction, extracted_at = _parse_filename("flights_arrival_20260430_171746.json")
        assert direction == "ARRIVAL"
        assert extracted_at == "'2026-04-30 17:17:46'"

    def test_returns_fallback_for_malformed(self):
        direction, extracted_at = _parse_filename("bad_filename.json")
        assert direction == "UNKNOWN"
        assert extracted_at == "CURRENT_TIMESTAMP()"

    def test_returns_fallback_for_wrong_pattern(self):
        direction, extracted_at = _parse_filename("flights_unknown_20260430_171746.json")
        assert direction == "UNKNOWN"
        assert extracted_at == "CURRENT_TIMESTAMP()"


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


class TestMain:
    """Tests for the main() orchestration function — no Snowflake connection."""

    def test_archives_file_on_success(self, monkeypatch):
        monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "test_account")
        monkeypatch.setenv("SNOWFLAKE_USER", "test_user")
        monkeypatch.setenv("SNOWFLAKE_PASSWORD", "test_pass")
        monkeypatch.setattr(SnowflakeLoader, "load_file", lambda self, path: True)

        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "flights_departure_20260515_120000.json")
            with open(src, "w") as f:
                f.write('{"test": "data"}\n')

            monkeypatch.setattr("load_flights.DATA_DIR", tmpdir)
            main()

            assert not os.path.exists(src)
            assert os.path.exists(
                os.path.join(tmpdir, "archive", os.path.basename(src))
            )

    def test_leaves_file_on_failure(self, monkeypatch):
        monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "test_account")
        monkeypatch.setenv("SNOWFLAKE_USER", "test_user")
        monkeypatch.setenv("SNOWFLAKE_PASSWORD", "test_pass")
        monkeypatch.setattr(SnowflakeLoader, "load_file", lambda self, path: False)

        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "flights_departure_20260515_120000.json")
            with open(src, "w") as f:
                f.write('{"test": "data"}\n')

            monkeypatch.setattr("load_flights.DATA_DIR", tmpdir)
            main()

            assert os.path.exists(src)
            assert not os.path.exists(
                os.path.join(tmpdir, "archive", os.path.basename(src))
            )
