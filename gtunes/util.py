# ===============
# General helpers
# ===============

import logging
import os

import dotenv

dotenv.load_dotenv()
log_level = os.getenv("GTUNES_LOG_LEVEL", "INFO").upper()
gtunes_logger = logging.getLogger('gtunes')
gtunes_logger.setLevel(log_level)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
gtunes_logger.addHandler(handler)

def get_logger() -> logging.Logger:
    return gtunes_logger

data_dir = os.getenv("GTUNES_DIR", os.path.join("gtunes", "data"))

def get_data_dir() -> str:
    return data_dir

# Accept timestamps in the format 1:30 where 1 is the minutes and 30 is the seconds
def timestamp_to_seconds(timestamp):
    sum(x * int(t) for x, t in zip([60, 1], timestamp.split(":")))