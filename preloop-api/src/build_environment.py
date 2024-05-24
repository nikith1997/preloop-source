import os


def is_local_dev() -> bool:
    """
    Check if the application is running in local development mode.

    :return: True if running in local development mode, False otherwise
    """
    if "IS_LOCAL_DEV_ENV" in os.environ:
        return True

    return False
