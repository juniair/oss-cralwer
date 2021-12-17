import logging, logging.config, logging.handlers
import json

# disable requests library log message.
urllib3_logger = logging.getLogger("requests")
urllib3_logger.setLevel(logging.CRITICAL)


log = logging.getLogger(__name__)
# log.setLevel(logging.INFO)
log.setLevel(logging.DEBUG)
formatter = logging.Formatter("[%(asctime)s][%(levelname)s] - [%(module)s].[%(funcName)s(line: %(lineno)d)] > %(message)s")


# Logger -> Singleton.
def getLogger(filename="logging.log", log_file_path="."):
    LOG_FILENAME = "{}/{}".format(log_file_path, filename)
    streamHandler = logging.StreamHandler()
    fileMaxByte = 1024 * 1024 * 1024
    fileHandler = logging.handlers.RotatingFileHandler(
        filename=LOG_FILENAME, maxBytes=fileMaxByte, backupCount=10
    )
    streamHandler.setFormatter(formatter)
    fileHandler.setFormatter(formatter)

    log.setLevel(level=logging.DEBUG)
    log.addHandler(streamHandler)
    log.addHandler(fileHandler)

    return log


def write_progress_log(
    category="development/development",
    page="0",
    number="0",
    PROGRESS_LOG_FILENAME="./progress.json",
):
    with open(PROGRESS_LOG_FILENAME, "w") as fp:
        json.dump(
            {
                "LAST_SEARCH_CATEGORY": category,
                "LAST_SEARCH_PAGE": page,
                "LAST_PROJECT_NUMBER": number,
            },
            fp,
        )
