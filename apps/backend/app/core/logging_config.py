import logging

_CONFIGURED = False


def configure_logging(log_level: str = "INFO") -> None:
    """Configure application logging once, at startup.

    Uses a simple stream handler that writes to stdout/stderr so logs are
    captured by the hosting platform (e.g. Render). Never log secrets, API
    keys, or raw uploaded image bytes anywhere in the application.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )

    # Replace existing handlers so we do not duplicate log lines on reload.
    root_logger.handlers = [handler]

    # Keep the application logger aligned with the configured level.
    logging.getLogger("app").setLevel(level)

    _CONFIGURED = True
