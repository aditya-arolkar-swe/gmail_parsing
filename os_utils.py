import os
import pickle
from logging import Logger


def create_folder_if_not_exists(directory) -> None:
    try:
        os.makedirs(directory, exist_ok=True)
        print(f"Directory '{directory}' created or already exists.")
    except Exception as e:
        print(f"An error occurred: {e}")


def read_file(filename: str, logger: Logger) -> dict:
    messages = {}
    if not os.path.exists(filename):
        return messages

    try:
        with open(filename, 'rb') as f:
            messages = pickle.load(f)
        logger.info(f"Loaded data from local file {os.path.join(os.path.curdir, filename)}!")
    except Exception as e:
        logger.error(f"Failed to load data from file: {e}")

    return messages


def write_file(data, filename, logger: Logger) -> None:
    try:
        with open(filename, 'wb') as f:
            pickle.dump(data, f)
        logger.info(f"Wrote data to local file {os.path.join(os.path.curdir, filename)}!")
    except Exception as e:
        logger.error(f"Failed to write data to file: {e}")

