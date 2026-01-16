# Set up a Logger at class level rather than at each instance creation
import logging
import os

formatter = logging.Formatter(
    "%(asctime)s %(process)d:%(thread)d %(levelname)s %(module)s:%(lineno)d %(message)s"
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger = logging.getLogger("Planner")
logger.addHandler(handler)
level: int | str = logging.DEBUG
if os.getenv("GITHUB_PM_LOG_LEVEL"):
    level = os.getenv("GITHUB_PM_LOG_LEVEL")
logger.setLevel(level)
