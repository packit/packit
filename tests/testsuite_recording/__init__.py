from tests.testsuite_recording.replacements import HANDLE_MODULE_LIST
from requre.import_system import upgrade_import_system

upgrade_import_system(HANDLE_MODULE_LIST, debug_file="modules.out")
