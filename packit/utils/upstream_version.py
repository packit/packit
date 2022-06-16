from logging import getLogger

try:
    from rebasehelper.plugins.plugin_manager import plugin_manager
except ImportError:
    from rebasehelper.versioneer import versioneers_runner


logger = getLogger(__name__)


def get_upstream_version(package_name):
    """Gets the latest upstream version of the specified package."""
    try:
        get_version = plugin_manager.versioneers.run
    except NameError:
        get_version = versioneers_runner.run
    return get_version(None, package_name, None)
