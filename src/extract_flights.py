import os
import json
import time
import requests
from datetime import datetime
from config import (
    get_logger, validate_api_config, API_URL, API_KEY, DATA_DIR,
    DEFAULT_LIMIT, API_MAX_RETRIES, API_RETRY_BACKOFF,
    API_MAX_PAGES, API_PAGE_DELAY
)

logger = get_logger("extract_flights")

class AviationAPIClient:
    """Client for interacting with the AviationStack API."""
    def __init__(self, 
                 api_url: str = API_URL, 
                 api_key: str = API_KEY,
                 max_retries: int = API_MAX_RETRIES,
                 backoff_factor: int = API_RETRY_BACKOFF,
                 page_delay: float = API_PAGE_DELAY,
                 max_pages: int = API_MAX_PAGES):
        """
        Parameters:
        api_url (str): The URL of the API endpoint.
        api_key (str): The API key for authentication.
        max_retries (int): The maximum number of retries for failed requests.
        backoff_factor (int): The factor to multiply by for each retry (exponential backoff).
        page_delay (float): The delay between page requests to respect rate limits.
        max_pages (int): The maximum number of pages to fetch.
        """

        self.api_url = api_url
        self.api_key = api_key
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.page_delay = page_delay
        self.max_pages = max_pages
        self.session = requests.Session()
        
    def fetch_flights(self, limit: int = 100, **api_filters) -> list:
        """Fetch all pages of flights for the given filters."""

        logger.info(f"Fetching flights with filters: {api_filters}...")

        all_flights = []
        offset = 0
        page_count = 0

        while True:
            page_count += 1
            if page_count > self.max_pages:
                logger.warning(f"Reached max_pages limit ({self.max_pages}). "
                               f"Retrieved {len(all_flights)} records — data may be incomplete.")
                break

            params = {
                'access_key': self.api_key,
                'limit': limit,
                'offset': offset
            }
            params.update(api_filters)

            # Retry loop with exponential backoff (5xx/network only, not 4xx)
            for attempt in range(self.max_retries + 1):
                try:
                    response = self.session.get(self.api_url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    break
                except requests.exceptions.HTTPError as e:
                    if response is not None and 400 <= response.status_code < 500:
                        logger.error(f"API Request failed (client error, not retrying): {e}")
                        return all_flights
                    if attempt < self.max_retries:
                        delay = self.backoff_factor ** attempt
                        logger.warning(
                            f"Request failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                            f"Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"API Request failed after {self.max_retries + 1} attempts: {e}")
                        return all_flights
                except requests.exceptions.RequestException as e:
                    if attempt < self.max_retries:
                        delay = self.backoff_factor ** attempt
                        logger.warning(
                            f"Request failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                            f"Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"API Request failed after {self.max_retries + 1} attempts: {e}")
                        return all_flights

            if 'error' in data:
                logger.error(f"API Error: {data['error'].get('message', 'Unknown Error')}")
                break

            flights = data.get('data', [])
            all_flights.extend(flights)

            pagination = data.get('pagination', {})
            total = pagination.get('total', 0)
            count = pagination.get('count', 0)

            logger.info(f"Retrieved {len(all_flights)} / {total} records (page {page_count}).")

            if len(all_flights) >= total or count == 0:
                break

            offset += limit
            time.sleep(self.page_delay)

        return all_flights

def save_to_ndjson(flights: list, label: str, data_dir: str) -> str:
    """Save the list of flight dictionaries to a local NDJSON file."""
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(data_dir, f"flights_{label.lower()}_{timestamp}.json")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        for flight in flights:
            f.write(json.dumps(flight) + '\n')
            
    logger.info(f"Saved {len(flights)} {label} records to {filepath}")
    return filepath

def main():
    logger.info("=== Starting Aviation Data Extraction ===")
    
    try:
        validate_api_config()
    except ValueError as e:
        logger.error(e)
        return

    client = AviationAPIClient()
    
    # Target airport can be dynamically passed via CLI/Args in the future.
    target_airport = "YTZ"

    extraction_tasks = [
        {"label": "DEPARTURE", "filters": {"dep_iata": target_airport}},
        {"label": "ARRIVAL", "filters": {"arr_iata": target_airport}}
    ]
    
    for task in extraction_tasks:
        label = task["label"]
        filters = task["filters"]
        
        flights = client.fetch_flights(limit=DEFAULT_LIMIT, **filters)
        
        if not flights:
            logger.warning(f"No {label} flights found or an error occurred. Skipping.")
            continue

        save_to_ndjson(flights, label, DATA_DIR)
            
    logger.info("=== Extraction Complete ===")

if __name__ == "__main__":
    main()
