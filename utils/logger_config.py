from typing import Union, Optional

from loguru import logger
from sys import stderr


def setup_logger(
        level: Union[str, int] = "DEBUG", colorize: Optional[bool] = True, as_session=False
):
    logger.remove()
    logger.add(
        sink=stderr,
        level=level,
        colorize=colorize,
        enqueue=True,
        format="<red>{line}:{module}</red> <lvl>{level}</lvl> - <lvl>{message}</lvl>",
    )

    if as_session:
        log_file = "file_{time}.log"
        level = "DEBUG"
        logger.add(
            log_file,
            format="{time:MM-DD at HH:mm:ss} | {level} | {message}",
            level=level,
            rotation="5 MB",
        )
        logger.info("Logging setuped succesfully")
