# Copyright (C) 2021 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only

import json
import os
from pathlib import Path
from shutil import copyfile

import urllib3 as urllib
import yaml
from url_normalize import url_normalize

from .datasources.datasources import Datasources
from .namespace import Namespace
from .repo import Repo
from .teams_connector import TeamsConnector


class Config(Namespace):
    """Configuration object. Also contains datasources for use."""
    args: Namespace
    cwd: os.PathLike
    datasources: Datasources = Datasources()
    teams_connector: TeamsConnector
    GERRIT_HOST: str
    GERRIT_STATE_PATH: str
    GERRIT_USERNAME: str
    GERRIT_PASSWORD: str
    MS_TEAMS_NOTIFY_URL: str
    state_repo: Repo
    state_data: dict[str, Repo] = {}
    _state_ref: str = None
    qt5_default: dict[str, Repo] = {}
    suppress_warn: bool = False
    REPOS: list[str]
    NON_BLOCKING_REPOS: list[str] = []
    rewind_module: Repo = None
    drop_dependency: Repo = None
    drop_dependency_from: list[Repo] = None


def _load_config(file, args):
    """Load configuration from disk or environment"""
    cwd = Path(__file__).parent.parent
    file = cwd.joinpath(file)
    c = dict()
    if file.exists():
        with open(file) as config_file:
            c = yaml.load(config_file, Loader=yaml.SafeLoader)
    else:
        try:
            copyfile(file.parent / (file.name + ".template"), file)
            print("Config file not found, so we created 'config.yaml' from the template.")
            with open(file) as config_file:
                c = yaml.load(config_file)
        except FileNotFoundError:
            print("ERROR: Unable to load config because config.yaml, or config.yaml.template\n"
                  "was not found on disk. Please pull/checkout config.yaml.template from\n"
                  "the repo again.")

    for key in c.keys():
        if os.environ.get(key):
            print(f'Overriding config option {key} with environment variable.')
            c[key] = os.environ[key]
    config = Config(**c)
    config.cwd = cwd
    config.args = args
    config.GERRIT_HOST = url_normalize(config.GERRIT_HOST)
    config.teams_connector = TeamsConnector(config)
    ssh_file = Path(os.path.expanduser('~'), ".ssh", "config")
    if ssh_file.exists():
        with open(ssh_file) as ssh_config:
            contents = ssh_config.read()
            gerrit_base_url = urllib.util.parse_url(config.GERRIT_HOST).host
            loc = contents.find(gerrit_base_url)
            user_loc = contents.find("User", loc)
            user_name = contents[user_loc:contents.find("\n", user_loc)].split(" ")[1]
            if user_name:
                config._state_ref = f"refs/personal/{user_name or config.GERRIT_USERNAME}" \
                                    f"/submodule_updater"
    return config
