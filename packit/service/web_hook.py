# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import hmac
import logging
from concurrent.futures.thread import ThreadPoolExecutor
from hashlib import sha1

from flask import Flask, abort, request, jsonify

from packit.config import Config
from packit.jobs import SteveJobs
from packit.utils import set_logging


class PackitWebhookReceiver(Flask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_logging(level=logging.DEBUG)


app = PackitWebhookReceiver(__name__)
logger = logging.getLogger("packit")
threadpool_executor = ThreadPoolExecutor(max_workers=16)


@app.route("/healthz", methods=["GET", "HEAD", "POST"])
def get_health():
    # TODO: add some interesting stats here
    return jsonify({"msg": "We are healthy!"})


@app.route("/webhooks/github", methods=["POST"])
def github_webhook():
    msg = request.get_json()

    if not msg:
        logger.debug("/webhooks/github: we haven't received any JSON data.")
        return "We haven't received any JSON data."

    if all([msg.get("zen"), msg.get("hook_id"), msg.get("hook")]):
        logger.debug(f"/webhooks/github received ping event: {msg['hook']}")
        return "Pong!"

    config = Config.get_user_config()

    if not _validate_signature(config):
        abort(401)  # Unauthorized

    # GitHub terminates the conn after 10 seconds:
    # https://developer.github.com/v3/guides/best-practices-for-integrators/#favor-asynchronous-work-over-synchronous
    # as a temporary workaround, before we start using celery, let's just respond right away
    # and send github 200 that we got it
    threadpool_executor.submit(_give_event_to_steve, msg, config)

    return "Webhook accepted. We thank you, Github."


def _validate_signature(config: Config) -> bool:
    """
    https://developer.github.com/webhooks/securing/#validating-payloads-from-github
    https://developer.github.com/webhooks/#delivery-headers
    """
    if "X-Hub-Signature" not in request.headers:
        # no signature -> no validation
        return True

    sig = request.headers["X-Hub-Signature"]
    if not sig.startswith("sha1="):
        logger.warning(f"Digest mode in X-Hub-Signature {sig!r} is not sha1")
        return False

    webhook_secret = config.webhook_secret.encode()
    if not webhook_secret:
        logger.warning("webhook_secret not specified in config")
        # For now, don't let this stop us, but long-term return False here
        return True

    signature = sig.split("=")[1]
    mac = hmac.new(webhook_secret, msg=request.get_data(), digestmod=sha1)
    digest_is_valid = hmac.compare_digest(signature, mac.hexdigest())
    if digest_is_valid:
        logger.debug(f"/webhooks/github payload signature OK.")
    else:
        logger.warning(f"/webhooks/github payload signature validation failed.")
        logger.debug(f"X-Hub-Signature: {sig!r} != computed: {mac.hexdigest()}")
    return digest_is_valid


def _give_event_to_steve(event: dict, config: Config):
    try:
        steve = SteveJobs(config)
        steve.process_message(event)
    except Exception as ex:
        logger.error("There was an exception while processing the event.")
        logger.exception(ex)
