import logging
import time
import gtunes.spot_select as spot_select
from textual.color import Color
import asyncio

# TODO: need to add a fast way of populating the selector
# maybe an optional scrape-data argument, or scrape-data queue
async def test_spot_select_app():
    example_tune = "The Ashplant"
    _ = []
    app = spot_select.SpotApp(example_tune, _)
    async with app.run_test() as pilot:
        time.sleep(0.2)
        logging.debug("Test pressing q")

        await pilot.press("q")