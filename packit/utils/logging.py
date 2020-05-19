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

import logging
import threading

logger = logging.getLogger(__name__)


class StreamLogger(threading.Thread):
    def __init__(self, stream, log_level=logging.DEBUG, decode=False):
        super().__init__(daemon=True)
        self.stream = stream
        self.output = []
        self.log_level = log_level
        self.decode = decode

    def run(self):
        for line in self.stream:
            # not doing strip here on purpose so we get real output
            # and we are saving bytes b/c the output can contain chars which can't be decoded
            self.output.append(line)
            line = line.rstrip(b"\n")
            if self.decode:
                line = line.decode()
            logger.log(self.log_level, line)

    def get_output(self):
        return b"".join(self.output)


class PackitFormatter(logging.Formatter):
    def format(self, record):
        if record.levelno == logging.INFO:
            self._style._fmt = "%(message)s"
        elif record.levelno > logging.INFO:
            self._style._fmt = "%(levelname)-8s %(message)s"
        else:  # debug
            self._style._fmt = (
                "%(asctime)s.%(msecs).03d %(filename)-17s %(levelname)-6s %(message)s"
            )
        return logging.Formatter.format(self, record)


def set_logging(
    logger_name="packit",
    level=logging.INFO,
    handler_class=logging.StreamHandler,
    handler_kwargs=None,
    date_format="%H:%M:%S",
):
    """
    Set personal logger for this library.

    :param logger_name: str, name of the logger
    :param level: int, see logging.{DEBUG,INFO,ERROR,...}: level of logger and handler
    :param handler_class: logging.Handler instance, default is StreamHandler (/dev/stderr)
    :param handler_kwargs: dict, keyword arguments to handler's constructor
    :param date_format: str, date style in the logs
    """
    if level == logging.NOTSET:
        return

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.debug(f"Logging set to {logging.getLevelName(level)}")

    # do not readd handlers if they are already present
    if not [x for x in logger.handlers if isinstance(x, handler_class)]:
        handler_kwargs = handler_kwargs or {}
        handler = handler_class(**handler_kwargs)
        handler.setLevel(level)

        formatter = PackitFormatter(None, date_format)
        handler.setFormatter(formatter)
        logger.addHandler(handler)


def commits_to_nice_str(commits):
    return "\n".join(
        f"{commit.summary}\n"
        f"Author: {commit.author.name} <{commit.author.email}>\n"
        f"{commit.hexsha}\n"
        for commit in commits
    )
