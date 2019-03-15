"""
Interface for downstream checks
"""
import logging


logger = logging.getLogger(__name__)
checks = {}


def downstream_check(kls):
    checks[kls.name] = kls
    return kls


class DownstreamCheck:
    # the link on the right in a list of checks on github
    url = ""
    # text in italics
    status = "pending"
    # the text next to the status
    description = ""
    # label in bold next to the icon
    name = ""


# we should add one more layer to this abstraction, something like a profile
# because people won't be able to pick these, that will be our responsibility to define
# checks which will be executed for a given platform, so in order to integrate with
# fedora rawhide, you would need to pass simple-koji-ci and Fedora CI
@downstream_check
class SimpleKojiBuild(DownstreamCheck):
    url = "https://pagure.io/fedora-ci/simple-koji-ci"
    description = "Fedora build"
    name = "simple-koji-ci"


@downstream_check
class AllPackagesCI(DownstreamCheck):
    # this is actually for rawhide
    url = (
        "https://jenkins-continuous-infra.apps.ci.centos.org/view/"
        "Fedora%20All%20Packages%20Pipeline/job/fedora-rawhide-build-pipeline/"
    )
    description = "Fedora test run"
    name = "Fedora CI"


def get_check_by_name(name: str) -> DownstreamCheck:
    """
    Get instance of check for the specific name

    :param name: str, name of the check
    :return: instance of DownstreamCheck
    """
    try:
        return checks[name]()
    except KeyError:
        logger.error("no such check %s", name)
        raise RuntimeError("There is no such downstream check: %s", name)
