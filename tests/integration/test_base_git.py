from flexmock import flexmock

from packit.actions import ActionName
from packit.base_git import PackitRepositoryBase
from packit.config import PackageConfig, Config

# TODO rename it to
# from sandcastle.api import Sandcastle
# as https://github.com/packit-service/sandcastle/pull/9
# is merged
from generator.deploy_openshift_pod import OpenshiftDeployer


def test_get_output_from_action_defined():
    echo_cmd = "echo 'hello world'"

    packit_repository_base = PackitRepositoryBase(
        config=flexmock(Config()),
        package_config=flexmock(PackageConfig(actions={ActionName.pre_sync: echo_cmd})),
    )

    packit_repository_base.local_project = flexmock(working_dir=".")

    result = packit_repository_base.get_output_from_action(ActionName.pre_sync)
    assert result == "hello world\n"


def test_get_output_from_action_defined_in_sandcastle_object():
    echo_cmd = "hello world"
    flexmock(OpenshiftDeployer).should_receive("get_api_client").and_return("something")
    packit_repository_base = PackitRepositoryBase(
        config=flexmock(Config()),
        package_config=flexmock(PackageConfig(actions={ActionName.pre_sync: echo_cmd})),
        sandcastle_object=OpenshiftDeployer(
            image_reference="fooimage", k8s_namespace_name="default"
        ),
    )
    packit_repository_base.config.actions_environment = "sandcastle"

    flexmock(OpenshiftDeployer).should_receive("exec").and_return(echo_cmd)
    result = packit_repository_base.get_output_from_action(ActionName.pre_sync)
    assert result == "hello world"
