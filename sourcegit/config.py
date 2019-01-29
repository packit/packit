import json
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import click


@dataclass
class Config:
    verbose: bool
    debug: bool
    fas_user: str
    keytab: str


pass_config = click.make_pass_decorator(Config)


def get_default_map_from_file() -> Optional[dict]:
    config_path = ".sourcegit"
    if os.path.isfile(config_path):
        with open(config_path) as config_data:
            return json.load(config_data)
    return None


@lru_cache()
def get_context_settings() -> dict:
    return dict(help_option_names=['-h', '--help'],
                auto_envvar_prefix='SOURCE_GIT',
                default_map=get_default_map_from_file())
