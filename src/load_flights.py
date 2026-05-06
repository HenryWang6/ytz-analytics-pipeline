import os
import re
import shutil
import snowflake.connector
from config import (
    get_logger, validate_snowflake_config, DATA_DIR, 
    SF_ACCOUNT, SF_USER, SF_PASSWORD, SF_ROLE, 
    SF_WAREHOUSE, SF_DATABASE, SF_SCHEMA
)

logger = get_logger("load_flights")


def _extract_direction(filename: str) -> str:
    """Extract direction label from a flights_{direction}_{timestamp}.json filename."""
    match = re.match(r'flights_(departure|arrival)_\d{8}_\d{6}\.json', filename, re.IGNORECASE)
    return match.group(1).upper() if match else "UNKNOWN"


class SnowflakeLoader:
    """Client for securely connecting to and loading data into Snowflake."""
    def __init__(self, account, user, password, role, warehouse, database, schema):
        self.account = account
        self.user = user
        self.password = password
        self.role = role
        self.warehouse = warehouse
        self.database = database
        self.schema = schema
        
    def load_file(self, filepath: str) -> bool:
        """Uploads a local NDJSON file to the Snowflake Stage and executes COPY INTO."""
        filename = os.path.basename(filepath)
        direction = _extract_direction(filename)
        target_airport = "YTZ"
        
        logger.info(f"Connecting to Snowflake to load {filename}...")
        
        try:
            conn = snowflake.connector.connect(
                user=self.user,
                password=self.password,
                account=self.account,
                role=self.role,
                warehouse=self.warehouse,
                database=self.database,
                schema=self.schema
            )
            
            cursor = conn.cursor()
            
            # 1. PUT command to upload the file to the internal stage
            put_command = f"PUT file://{filepath} @AVIATION_STAGE AUTO_COMPRESS=TRUE OVERWRITE=TRUE;"
            logger.info("Executing PUT command...")
            cursor.execute(put_command)
            
            # 2. COPY INTO command
            filename_in_stage = filename + ".gz"
            copy_command = f"""
            COPY INTO RAW_FLIGHTS (RAW_JSON, EXTRACTED_AT, DIRECTION, TARGET_AIRPORT)
            FROM (
                SELECT 
                    $1, 
                    CURRENT_TIMESTAMP(), 
                    '{direction}', 
                    '{target_airport}'
                FROM @AVIATION_STAGE/{filename_in_stage}
            )
            FILE_FORMAT = (TYPE = JSON);
            """
            
            logger.info("Executing COPY INTO command...")
            cursor.execute(copy_command)
            
            results = cursor.fetchall()
            logger.info(f"Load successful. File loaded: {results[0][0]}, Rows parsed: {results[0][3]}")
            return True
            
        except Exception as e:
            logger.error(f"Snowflake Error: {e}")
            return False
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

def get_pending_files(data_dir: str) -> list:
    """Scan the data directory for any .json files to load."""
    if not os.path.exists(data_dir):
        return []
    return [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.json')]

def main():
    logger.info("=== Starting Aviation Data Load ===")
    
    try:
        validate_snowflake_config()
    except ValueError as e:
        logger.error(e)
        return
        
    files = get_pending_files(DATA_DIR)
    
    if not files:
        logger.info(f"No pending files found in {DATA_DIR}. Exiting.")
        return
        
    loader = SnowflakeLoader(
        account=SF_ACCOUNT, user=SF_USER, password=SF_PASSWORD,
        role=SF_ROLE, warehouse=SF_WAREHOUSE, database=SF_DATABASE, schema=SF_SCHEMA
    )
        
    for filepath in files:
        success = loader.load_file(filepath)
        
        if success:
            archive_dir = os.path.join(os.path.dirname(filepath), "archive")
            os.makedirs(archive_dir, exist_ok=True)
            archived_path = os.path.join(archive_dir, os.path.basename(filepath))
            shutil.move(filepath, archived_path)
            logger.info(f"Archived loaded file to {archived_path}")
        else:
            logger.warning(f"Skipping archive for {filepath} due to load error.")
            
    logger.info("=== Load Complete ===")

if __name__ == "__main__":
    main()
