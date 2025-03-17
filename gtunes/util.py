# ===============
# General helpers
# ===============

import logging
import os
import pathlib

import dotenv

dotenv.load_dotenv()

gtunes_test = os.getenv("GTUNES_TEST") == "true"

if gtunes_test:
    log_level = "DEBUG"
else:
    log_level = os.getenv("GTUNES_LOG_LEVEL", "INFO").upper()

gtunes_logger = logging.getLogger('gtunes')
gtunes_logger.setLevel(log_level)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
gtunes_logger.addHandler(handler)

def get_logger() -> logging.Logger:
    return gtunes_logger

default_data_dir = str(pathlib.Path.cwd() / "gtunes" / "data")
if gtunes_test:
    data_dir = default_data_dir
else:
    data_dir = os.getenv("GTUNES_DIR", default_data_dir)

def get_data_dir() -> str:
    return data_dir

# Accept timestamps in the format 1:30 where 1 is the minutes and 30 is the seconds
def timestamp_to_seconds(timestamp):
    sum(x * int(t) for x, t in zip([60, 1], timestamp.split(":")))