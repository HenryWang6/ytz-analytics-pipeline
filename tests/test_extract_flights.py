import os
import sys
import json
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from extract_flights import AviationAPIClient, save_to_ndjson


class TestAviationAPIClient:
    """Tests for the AviationStack API client — always mocks the API."""

    def test_init_sets_attributes(self):
        client = AviationAPIClient(
            api_url="https://api.example.com/v1/flights",
            api_key="test_key_123",
        )
        assert client.api_url == "https://api.example.com/v1/flights"
        assert client.api_key == "test_key_123"

    def test_fetch_flights_single_page(self, requests_mock):
        client = AviationAPIClient(
            api_url="https://api.example.com/v1/flights",
            api_key="test_key",
        )
        requests_mock.get(
            "https://api.example.com/v1/flights",
            json={
                "data": [{"flight_date": "2026-05-06", "flight": {"iata": "PD101"}}],
                "pagination": {"total": 1, "count": 1},
            },
        )
        flights = client.fetch_flights(limit=100, dep_iata="YTZ")
        assert len(flights) == 1
        assert flights[0]["flight"]["iata"] == "PD101"

    def test_fetch_flights_paginates(self, requests_mock):
        client = AviationAPIClient(
            api_url="https://api.example.com/v1/flights",
            api_key="test_key",
            max_pages=2,
            page_delay=0,
        )
        responses = [
            {
                "data": [{"id": 1}],
                "pagination": {"total": 2, "count": 1},
            },
            {
                "data": [{"id": 2}],
                "pagination": {"total": 2, "count": 1},
            },
        ]
        requests_mock.get(
            "https://api.example.com/v1/flights",
            json=responses[0],
        )

        def paginated_response(request, context):
            offset = int(request.qs.get("offset", [0])[0])
            return responses[offset // 100]

        requests_mock.get(
            "https://api.example.com/v1/flights",
            json=paginated_response,
        )
        flights = client.fetch_flights(limit=100, dep_iata="YTZ")
        assert len(flights) == 2

    def test_fetch_flights_handles_api_error(self, requests_mock):
        client = AviationAPIClient(
            api_url="https://api.example.com/v1/flights",
            api_key="test_key",
        )
        requests_mock.get(
            "https://api.example.com/v1/flights",
            json={"error": {"message": "Invalid API key"}},
        )
        flights = client.fetch_flights(limit=100, dep_iata="YTZ")
        assert flights == []

    def test_fetch_flights_handles_http_error(self, requests_mock):
        client = AviationAPIClient(
            api_url="https://api.example.com/v1/flights",
            api_key="test_key",
        )
        requests_mock.get(
            "https://api.example.com/v1/flights",
            status_code=500,
        )
        flights = client.fetch_flights(limit=100, dep_iata="YTZ")
        assert flights == []

    def test_fetch_flights_retries_on_transient_error(self, requests_mock):
        client = AviationAPIClient(
            api_url="https://api.example.com/v1/flights",
            api_key="test_key",
            max_retries=2,
            backoff_factor=0,
        )
        call_count = {"count": 0}

        def flaky_response(request, context):
            call_count["count"] += 1
            if call_count["count"] <= 2:
                context.status_code = 500
                return {"error": "server error"}
            return {
                "data": [{"flight_date": "2026-05-06", "flight": {"iata": "PD101"}}],
                "pagination": {"total": 1, "count": 1},
            }

        requests_mock.get(
            "https://api.example.com/v1/flights",
            json=flaky_response,
        )
        flights = client.fetch_flights(limit=100, dep_iata="YTZ")
        assert len(flights) == 1
        assert flights[0]["flight"]["iata"] == "PD101"
        assert call_count["count"] == 3

    def test_fetch_flights_max_pages_cap(self, requests_mock):
        client = AviationAPIClient(
            api_url="https://api.example.com/v1/flights",
            api_key="test_key",
            max_pages=2,
            page_delay=0,
        )

        def paginated_response(request, context):
            offset = int(request.qs.get("offset", [0])[0])
            page_num = offset // 100
            return {
                "data": [{"id": offset + i} for i in range(100)],
                "pagination": {"total": 500, "count": 100},
            }

        requests_mock.get(
            "https://api.example.com/v1/flights",
            json=paginated_response,
        )
        flights = client.fetch_flights(limit=100, dep_iata="YTZ")
        assert len(flights) == 200

    def test_fetch_flights_includes_flight_date(self, requests_mock):
        client = AviationAPIClient(
            api_url="https://api.example.com/v1/flights",
            api_key="test_key",
        )
        requests_mock.get(
            "https://api.example.com/v1/flights",
            json={"data": [], "pagination": {"total": 0, "count": 0}},
        )
        client.fetch_flights(limit=100, dep_iata="YTZ", flight_date="2026-05-06")
        assert requests_mock.last_request.qs["flight_date"] == ["2026-05-06"]


class TestSaveToNdjson:
    def test_creates_file_with_correct_content(self):
        flights = [{"flight_date": "2026-05-06", "flight": {"iata": "PD101"}}]
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = save_to_ndjson(flights, "DEPARTURE", tmpdir)
            assert os.path.exists(filepath)
            assert "departure" in filepath.lower()
            with open(filepath) as f:
                lines = f.readlines()
            assert len(lines) == 1
            assert json.loads(lines[0])["flight"]["iata"] == "PD101"

    def test_creates_data_dir_if_missing(self):
        flights = [{"flight_date": "2026-05-06"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "subdir")
            save_to_ndjson(flights, "ARRIVAL", nested)
            assert os.path.isdir(nested)
