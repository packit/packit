from requre.helpers.files import StoreFiles
from requre.helpers.function_output import store_function_output
from requre.helpers.git.pushinfo import PushInfoStorageList
from requre.helpers.requests_response import RequestResponseHandling
from requre.helpers.tempfile import TempFile
from requre.import_system import upgrade_import_system

upgraded_import_system = (
    upgrade_import_system(debug_file="modules.out")
    .decorate(
        where="download_helper",
        what="DownloadHelper.request",
        who_name="lookaside_cache_helper",
        decorator=RequestResponseHandling.decorator_plain,
    )
    .decorate(
        where="^requests$",
        who_name=["lookaside_cache_helper", "^copr", "packit.distgit"],
        what="Session.send",
        decorator=RequestResponseHandling.decorator(item_list=[]),
    )
    .replace_module(where="^tempfile$", who_name="^packit", replacement=TempFile)
    .decorate(
        where="^packit$",
        who_name="fedpkg",
        what="utils.run_command_remote",
        decorator=store_function_output,
    )
    .decorate(
        where="fedpkg",
        what="FedPKG.clone",
        decorator=StoreFiles.arg_references(files_params={"target_path": 2}),
    )
    .decorate(
        where="git",
        who_name="local_project",
        what="remote.Remote.push",
        decorator=PushInfoStorageList.decorator(item_list=[]),
    )
    .decorate(  # ogr
        where="^requests$",
        what="Session.send",
        who_name=[
            "ogr.services.pagure",
            "gitlab",
            "github.MainClass",
            "github.Requester",
            "ogr.services.github_tweak",
        ],
        decorator=RequestResponseHandling.decorator(item_list=[]),
    )
)
