import os
import logging
from dotenv import load_dotenv

# Load environment variables once for the whole project
load_dotenv()

# --- Directories ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# --- Aviation API Config ---
API_KEY = os.getenv("AVIATION_API_KEY")
API_URL = os.getenv("AVIATION_API_URL", "http://api.aviationstack.com/v1/flights")
DEFAULT_LIMIT = int(os.getenv("AVIATION_API_LIMIT", "100"))
API_MAX_RETRIES = 3
API_RETRY_BACKOFF = 2
API_MAX_PAGES = 1
API_PAGE_DELAY = 1.0

# --- Snowflake Config ---
SF_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SF_USER = os.getenv("SNOWFLAKE_USER")
SF_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SF_ROLE = os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN")
SF_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
SF_DATABASE = os.getenv("SNOWFLAKE_DATABASE", "RAW_DB")
SF_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "AVIATION")
SF_STAGE = os.getenv("SNOWFLAKE_STAGE", "AVIATION_STAGE")
SF_TABLE = os.getenv("SNOWFLAKE_TABLE", "RAW_FLIGHTS")

def get_logger(name: str) -> logging.Logger:
    """Returns a configured logger instance."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def validate_api_config():
    if not API_KEY or API_KEY == "your_aviationstack_or_opensky_api_key_here":
        raise ValueError("AVIATION_API_KEY is missing or invalid in .env")

def validate_snowflake_config():
    if not all([SF_ACCOUNT, SF_USER, SF_PASSWORD]) or SF_ACCOUNT == "your_account_locator":
        raise ValueError("Missing or invalid Snowflake credentials in .env")
