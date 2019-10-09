from requre.import_system import ReplaceType
from requre.helpers.requests_response import RequestResponseHandling
from requre.helpers.tempfile import TempFile
from requre.helpers.git.pushinfo import PushInfoStorageList
from requre.helpers.function_output import store_function_output
from requre.helpers.files import StoreFiles
from requre.replacements import ogr

"""
Replacements based on requre import format
for more details see project https://github.com/packit-service/requre
"""

session_send = {
    "Session.send": [
        ReplaceType.DECORATOR,
        RequestResponseHandling.decorator(item_list=[]),
    ]
}

REBASE_HELPER: list = [
    (
        "download_helper",
        {"who_name": "lookaside_cache_helper"},
        {
            "DownloadHelper.request": [
                ReplaceType.DECORATOR,
                RequestResponseHandling.decorator_plain,
            ]
        },
    ),
    ("^requests$", {"who_name": "lookaside_cache_helper"}, session_send),
]
COPR: list = [("^requests$", {"who_name": "^copr"}, session_send)]
# replace of tempfile is important to get consistent push info data about dirs from git
PACKIT: list = [
    (
        "^tempfile$",
        {"who_name": "^packit"},
        {"": [ReplaceType.REPLACE_MODULE, TempFile]},
    ),
    ("^requests$", {"who_name": "packit.distgit"}, session_send),
    (
        "^packit$",
        {"who_name": "fedpkg"},
        {"utils.run_command_remote": [ReplaceType.DECORATOR, store_function_output]},
    ),
    (
        "fedpkg",
        {},
        {
            "FedPKG.clone": [
                ReplaceType.DECORATOR,
                StoreFiles.arg_references(files_params={"target_path": 2}),
            ]
        },
    ),
]
GIT: list = [
    (
        "git",
        {"who_name": "local_project"},
        {
            "remote.Remote.push": [
                ReplaceType.DECORATOR,
                PushInfoStorageList.decorator(item_list=[]),
            ]
        },
    )
]
HANDLE_MODULE_LIST = ogr.MODULE_LIST + REBASE_HELPER + COPR + PACKIT + GIT
