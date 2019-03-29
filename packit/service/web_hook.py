from flask import Flask, request
import logging
from io import StringIO

from packit.config import Config
from packit.bot_api import PackitBotAPI

app = Flask(__name__)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


@app.route("/github_release", methods=["POST"])
def github_release():
    msg = request.get_json()

    buffer = StringIO()
    logHandler = logging.StreamHandler(buffer)
    logHandler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)

    logger.debug(
        f"Received release event: "
        f"{msg['repository']['owner']}/{msg['repository']['name']} - {msg['release']['tag_name']}"
    )

    config = Config()
    api = PackitBotAPI(config)
    # Using fedmsg since the fields are the same
    api.sync_upstream_release_with_fedmsg({"msg": msg})

    logger.removeHandler(logHandler)
    buffer.flush()

    return buffer.getvalue()
