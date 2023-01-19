# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import copy
import json
from logging import getLogger
from typing import Dict, Any, Optional, Mapping, Union, List

from marshmallow import (
    Schema,
    fields,
    post_load,
    pre_load,
    post_dump,
    validates_schema,
    ValidationError,
)
from marshmallow_enum import EnumField

from packit.actions import ActionName
from packit.config import (
    PackageConfig,
    Config,
    CommonPackageConfig,
    Deployment,
)
from packit.config.job_config import (
    JobType,
    JobConfig,
    JobConfigTriggerType,
    get_default_jobs,
)
from packit.config.notifications import NotificationsConfig
from packit.config.notifications import PullRequestNotificationsConfig
from packit.config.sources import SourcesItem
from packit.constants import CHROOT_SPECIFIC_COPR_CONFIGURATION
from packit.sync import SyncFilesItem
from packit.config.aliases import DEPRECATED_TARGET_MAP

logger = getLogger(__name__)


class StringOrListOfStringsField(fields.Field):
    """Field type expecting a string or a list"""

    def _serialize(self, value, attr, obj, **kwargs) -> List[str]:
        return [str(item) for item in value]

    def _deserialize(self, value, attr, data, **kwargs) -> List[str]:
        if isinstance(value, list) and all(isinstance(v, str) for v in value):
            return value
        elif isinstance(value, str):
            return [value]
        else:
            raise ValidationError(
                f"Expected 'list[str]' or 'str', got {type(value)!r}."
            )


class SyncFilesItemSchema(Schema):
    """Schema for SyncFilesItem"""

    src = StringOrListOfStringsField()
    dest = fields.String()
    mkpath = fields.Boolean(default=False)
    delete = fields.Boolean(default=False)
    filters = fields.List(fields.String(), missing=None)


class FilesToSyncField(fields.Field):
    """
    Field type representing SyncFilesItem

    This is needed in order to handle entries which are strings, instead
    of a dict matching SyncFilesItemSchema.
    """

    def _serialize(self, value: Any, attr: str, obj: Any, **kwargs) -> List[dict]:
        return SyncFilesItemSchema().dump(value)

    def _deserialize(
        self,
        value: Any,
        attr: Optional[str],
        data: Optional[Mapping[str, Any]],
        **kwargs,
    ) -> SyncFilesItem:
        if isinstance(value, dict):
            return SyncFilesItem(**SyncFilesItemSchema().load(value))
        elif isinstance(value, str):
            return SyncFilesItem(src=[value], dest=value)
        else:
            raise ValidationError(f"Expected 'dict' or 'str', got {type(value)!r}.")


class ActionField(fields.Field):
    """
    Field class representing Action.
    """

    def _serialize(self, value: Any, attr: str, obj: Any, **kwargs):
        return {action_name.value: val for action_name, val in value.items()}

    def _deserialize(
        self,
        value: Any,
        attr: Optional[str],
        data: Optional[Mapping[str, Any]],
        **kwargs,
    ) -> Dict:
        if not isinstance(value, dict):
            raise ValidationError(f"'dict' required, got {type(value)!r}.")

        self.validate_all_actions(actions=list(value))
        return {ActionName(key): val for key, val in value.items()}

    def validate_all_actions(self, actions: list) -> None:
        """
        Validates all keys and raises exception with list of all invalid keys
        """
        invalid_actions = [
            action for action in actions if not ActionName.is_valid_action(action)
        ]

        if invalid_actions:
            raise ValidationError(f"Unknown action(s) provided: {invalid_actions}")


class NotProcessedField(fields.Field):
    """
    Field class to mark fields which will not be processed, only generates warning.
    Can be passed additional message via additional_message parameter.

    :param str additional_message: additional warning message to be displayed
    """

    def _serialize(self, value: Any, attr: str, obj: Any, **kwargs):
        raise NotImplementedError

    def _deserialize(
        self,
        value: Any,
        attr: Optional[str],
        data: Optional[Mapping[str, Any]],
        **kwargs,
    ):
        logger.warning(f"{self.name!r} is no longer being processed.")
        additional_message = self.metadata.get("additional_message")
        if additional_message:
            logger.warning(f"{additional_message}")


class SourceSchema(Schema):
    """
    Schema for sources.
    """

    path = fields.String(required=True)
    url = fields.String(required=True)

    @post_load
    def make_instance(self, data, **_):
        return SourcesItem(**data)


class PullRequestNotificationsSchema(Schema):
    """Configuration of commenting on pull requests."""

    successful_build = fields.Bool(default=False)

    @post_load
    def make_instance(self, data, **kwargs):
        return PullRequestNotificationsConfig(**data)


class NotificationsSchema(Schema):
    """Configuration of notifications."""

    pull_request = fields.Nested(PullRequestNotificationsSchema)

    @post_load
    def make_instance(self, data, **kwargs):
        return NotificationsConfig(**data)


class TargetsListOrDict(fields.Field):
    """Field type expecting a List[str] or Dict[str, Dict[str, Any]]
    Union is not supported by marshmallow so we have to validate manually :(
    https://github.com/marshmallow-code/marshmallow/issues/1191
    """

    @staticmethod
    def __is_targets_dict(value) -> bool:
        if (
            not isinstance(value, dict)
            or not all(isinstance(k, str) for k in value.keys())
            or not all(isinstance(v, dict) for v in value.values())
        ):
            return False
        # check the 'attributes', e.g. {'distros': ['centos-7']} or
        # {"additional_modules": "ruby:2.7,nodejs:12", "additional_packages": []}
        for attr in value.values():
            for key, value in attr.items():
                # distros is a list of str
                if key == "distros":
                    if isinstance(value, list) and all(
                        isinstance(distro, str) for distro in value
                    ):
                        return True
                    raise ValidationError(
                        f"Expected list[str], got {value!r} (type {type(value)!r})"
                    )
                # chroot-specific configuration:
                if key in CHROOT_SPECIFIC_COPR_CONFIGURATION.keys():
                    expected_type = CHROOT_SPECIFIC_COPR_CONFIGURATION[key].__class__
                    if isinstance(value, expected_type):
                        return True
                    raise ValidationError(
                        f"Expected {expected_type}, got {value!r} (type {type(value)!r})"
                    )
                raise ValidationError(f"Unknown key {key!r} in {attr!r}")
        return True

    def _deserialize(self, value, attr, data, **kwargs) -> Dict[str, Dict[str, Any]]:
        targets_dict: Dict[str, Dict[str, Any]]
        if isinstance(value, list) and all(isinstance(v, str) for v in value):
            targets_dict = {key: {} for key in value}
        elif self.__is_targets_dict(value):
            targets_dict = value
        else:
            raise ValidationError(
                f"Expected 'list[str]' or 'dict[str,dict]', got {value!r} (type {type(value)!r})."
            )

        for target in targets_dict.keys():
            if target in DEPRECATED_TARGET_MAP:
                logger.warning(
                    f"Target '{target}' is deprecated. Please update your configuration "
                    f"file and use '{DEPRECATED_TARGET_MAP[target]}' instead."
                )
        return targets_dict


class JobMetadataSchema(Schema):
    """Jobs metadata.

    TODO: to be removed after deprecation period.
          Will end also dist-git-branch and
          dist_git_branch deprecation period.
    """

    _targets = TargetsListOrDict(missing=None, data_key="targets")
    timeout = fields.Integer()
    owner = fields.String(missing=None)
    project = fields.String(missing=None)
    dist_git_branches = fields.List(fields.String(), missing=None)
    branch = fields.String(missing=None)
    scratch = fields.Boolean()
    list_on_homepage = fields.Boolean()
    preserve_project = fields.Boolean()
    use_internal_tf = fields.Boolean()
    additional_packages = fields.List(fields.String(), missing=None)
    additional_repos = fields.List(fields.String(), missing=None)
    fmf_url = fields.String(missing=None)
    fmf_ref = fields.String(missing=None)
    skip_build = fields.Boolean()
    env = fields.Dict(keys=fields.String(), missing=None)
    enable_net = fields.Boolean(missing=False)
    tmt_plan = fields.String(missing=None)
    tf_post_install_script = fields.String(missing=None)
    module_hotfixes = fields.Boolean()

    @pre_load
    def ordered_preprocess(self, data, **_):
        for key in ("dist-git-branch", "dist_git_branch"):
            if key in data:
                logger.warning(
                    f"Job metadata key {key!r} has been renamed to 'dist_git_branches', "
                    f"please update your configuration file."
                )
                data["dist_git_branches"] = data.pop(key)
        for key in ("targets", "dist_git_branches"):
            if isinstance(data.get(key), str):
                # allow key value being specified as string, convert to list
                data[key] = [data.pop(key)]

        return data


def validate_repo_name(value):
    """
    marshmallow validation for a repository name. Any
    filename is acceptable: No slash, no zero char.
    """
    if any(c in "/\0" for c in value):
        raise ValidationError("Repository name must be a valid filename.")
    return True


class CommonConfigSchema(Schema):
    """
    Common configuration options and methods for a package.
    """

    config_file_path = fields.String(missing=None)
    specfile_path = fields.String(missing=None)
    downstream_package_name = fields.String(missing=None)
    upstream_project_url = fields.String(missing=None)
    upstream_package_name = fields.String(missing=None, validate=validate_repo_name)
    paths = fields.List(fields.String())
    upstream_ref = fields.String(missing=None)
    upstream_tag_template = fields.String()
    archive_root_dir_template = fields.String()
    dist_git_url = NotProcessedField(
        additional_message="it is generated from dist_git_base_url and downstream_package_name",
        load_only=True,
    )
    dist_git_base_url = fields.String(mising=None)
    dist_git_namespace = fields.String(missing=None)
    allowed_gpg_keys = fields.List(fields.String(), missing=None)
    spec_source_id = fields.Method(
        deserialize="spec_source_id_fm", serialize="spec_source_id_serialize"
    )
    synced_files = fields.List(FilesToSyncField())
    files_to_sync = fields.List(FilesToSyncField())
    actions = ActionField(default={})
    create_pr = fields.Bool(default=True)
    sync_changelog = fields.Bool(default=False)
    create_sync_note = fields.Bool(default=True)
    patch_generation_ignore_paths = fields.List(fields.String(), missing=None)
    patch_generation_patch_id_digits = fields.Integer(
        missing=4, default=4, validate=lambda x: x >= 0
    )
    notifications = fields.Nested(NotificationsSchema)
    copy_upstream_release_description = fields.Bool(default=False)
    sources = fields.List(fields.Nested(SourceSchema), missing=None)
    merge_pr_in_ci = fields.Bool(default=True)
    srpm_build_deps = fields.List(fields.String(), missing=None)
    identifier = fields.String(missing=None)
    packit_instances = fields.List(EnumField(Deployment), missing=[Deployment.prod])
    issue_repository = fields.String(missing=None)
    release_suffix = fields.String(missing=None)
    update_release = fields.Bool(default=True)

    # Former 'metadata' keys
    _targets = TargetsListOrDict(missing=None, data_key="targets")
    timeout = fields.Integer()
    owner = fields.String(missing=None)
    project = fields.String(missing=None)
    dist_git_branches = fields.List(fields.String(), missing=None)
    branch = fields.String(missing=None)
    scratch = fields.Boolean()
    list_on_homepage = fields.Boolean()
    preserve_project = fields.Boolean()
    use_internal_tf = fields.Boolean()
    additional_packages = fields.List(fields.String(), missing=None)
    additional_repos = fields.List(fields.String(), missing=None)
    fmf_url = fields.String(missing=None)
    fmf_ref = fields.String(missing=None)
    env = fields.Dict(keys=fields.String(), missing=None)
    enable_net = fields.Boolean(missing=False)
    allowed_pr_authors = fields.List(fields.String(), missing=None)
    allowed_committers = fields.List(fields.String(), missing=None)
    tmt_plan = fields.String(missing=None)
    tf_post_install_script = fields.String(missing=None)
    module_hotfixes = fields.Boolean()

    # Image Builder integration
    image_distribution = fields.String(missing=None)
    # these two are freeform so that users can immediately use IB's new features
    image_request = fields.Dict(missing=None)
    image_customizations = fields.Dict(missing=None)
    copr_chroot = fields.String(missing=None)

    @staticmethod
    def spec_source_id_serialize(value: CommonPackageConfig):
        return value.spec_source_id

    @staticmethod
    def spec_source_id_fm(value: Union[str, int]):
        """
        method used in spec_source_id field.Method
        If value is int, it is transformed int -> "Source" + str(int)

        ex.
        1 -> "Source1"

        :return str: prepends "Source" in case input value is int
        """
        if value:
            try:
                value = int(value)
            except ValueError:
                # not a number
                pass
            else:
                # is a number!
                value = f"Source{value}"
        return value

    @post_load
    def make_instance(self, data, **_):
        return CommonPackageConfig(**data)

    @post_dump(pass_original=True)
    def adjust_files_to_sync(
        self, data: dict, original: CommonPackageConfig, **kwargs
    ) -> dict:
        """Fix the files_to_sync field in the serialized object

        B/c CommonPackageConfig.files_to_sync is a derived value, the meaning of the
        original configuration can be re-established only by checking the
        '_files_to_sync_used' attribute, and removing the 'files_to_sync' field from
        the serialized data if it's False.

        Args:
            data: Already serialized data.
            original: Original object being serialized.

        Returns:
            Modified serialized data with the 'files_to_sync' key removed if it was
            not used in the original object.
        """
        if not original._files_to_sync_used:
            data.pop("files_to_sync", None)
        return data


class JobConfigSchema(Schema):
    """
    Schema for processing JobConfig config data.
    """

    job = EnumField(JobType, required=True, attribute="type")
    trigger = EnumField(JobConfigTriggerType, required=True)
    skip_build = fields.Boolean()
    packages = fields.Dict(
        keys=fields.String(), values=fields.Nested(CommonConfigSchema())
    )

    @pre_load
    def ordered_preprocess(self, data, **_):
        for package, config in data.get("packages", {}).items():
            for key in ("targets", "dist_git_branches"):
                if isinstance(config, dict) and isinstance(config.get(key), str):
                    # allow key value being specified as string, convert to list
                    data["packages"][package][key] = [config.pop(key)]

        return data

    @validates_schema
    def specfile_path_defined(self, data, **_):
        """Check if a 'specfile_path' is specified for each package

        The only time 'specfile_path' is not required, is when the job is a
        'test' job.

        Args:
            data: partially loaded configuration data.

        Raises:
            ValidationError, if 'specfile_path' is not specified when
            it should be.
        """
        # Note: At this point, 'data' is still a dict, but values are already
        # loaded, this is why 'data["type"]' is already a JobType and not a string,
        # and the package configs below are PackageConfig objects, not dictionaries.
        if (data["type"] == JobType.tests and data.get("skip_build")) or data.get(
            "specfile_path"
        ):
            return

        errors = {}
        package: str
        config: PackageConfig
        for package, config in data.get("packages", {}).items():
            if not config.specfile_path:
                errors[package] = [
                    "'specfile_path' is not specified or "
                    "no specfile was found in the repo"
                ]
        if errors:
            raise ValidationError(errors)

    @post_load
    def make_instance(self, data, **_):
        return JobConfig(**data)


class PackageConfigSchema(Schema):
    """
    Schema for processing PackageConfig config data.

    This class is intended to handle all the logic that is internal
    to the configuration and it is possible to be done while loading
    or dumping the configuration.

    This includes, for example, setting default values which depend on
    the value of other keys, or validating key values according to the
    value of other keys.

    It does not include setting the value of keys based on context
    *external* to the config file (if there is a spec-file in the current
    path, for example).
    """

    jobs = fields.Nested(JobConfigSchema, many=True)
    packages = fields.Dict(
        keys=fields.String(), values=fields.Nested(CommonConfigSchema())
    )

    # list of deprecated keys and their replacement (new,old)
    deprecated_keys = (("upstream_package_name", "upstream_project_name"),)

    @pre_load
    def ordered_preprocess(self, data: dict, **_) -> dict:
        """Rename deprecated keys, and set defaults for 'packages' and 'jobs'

        Args:
            data: configuration dictionary as loaded from packit.yaml

        Returns:
            Transformed configuration dictionary with defaults
            for 'packages' and 'jobs' set.
        """
        # Create a deepcopy(), so that loading doesn't modify the
        # dictionary received.
        data = copy.deepcopy(data)
        data = self.rename_deprecated_keys(data)
        # Don't use 'setdefault' in this case, as we should expect
        # downstream_package_name only if there is no 'packages' key.
        if "packages" not in data:
            package_name = data.pop("downstream_package_name")
            paths = data.pop("paths", ["./"])
            data["packages"] = {
                package_name: {
                    "downstream_package_name": package_name,
                    "paths": paths,
                }
            }
        data.setdefault("jobs", get_default_jobs())
        # By this point, we expect both 'packages' and 'jobs' to be present
        # in the config.
        data = self.rearrange_packages(data)
        data = self.rearrange_jobs(data)
        logger.debug(f"Repo config after pre-loading:\n{json.dumps(data, indent=4)}")
        return data

    def rename_deprecated_keys(self, data: dict) -> dict:
        """
        Based on tuples stored in tuple cls.deprecated_keys, reassigns old keys values to new keys,
        in case new key is None and logs warning
        :param data: conf dictionary to process
        :return: processed dictionary
        """
        if not data:  # data is None when .packit.yaml is empty
            return data

        for new_key_name, old_key_name in self.deprecated_keys:
            old_key_value = data.get(old_key_name, None)
            if old_key_value:
                logger.warning(
                    f"{old_key_name!r} configuration key was renamed to {new_key_name!r},"
                    f" please update your configuration file."
                )
                new_key_value = data.get(new_key_name, None)
                if not new_key_value:
                    # prio: new > old
                    data[new_key_name] = old_key_value
                del data[old_key_name]
        return data

    @staticmethod
    def rearrange_packages(data: dict) -> dict:
        """Update package objects with top-level configuration values

        Top-level keys and values are copied to each package object if
        the given key is not set in that object already.

        Remove these keys from the top-level and return a dictionary
        containing only a 'packages' and 'jobs' key.

        Args:
            data: configuration dictionary, before any of the leaves
                having been loaded.

        Returns:
            A re-arranged configuration dictionary.
        """
        # Pop 'packages' and 'jobs' in order for 'data'
        # to contain only keys other then these when it comes
        # to merging it bellow.
        packages = data.pop("packages")
        jobs = data.pop("jobs")
        for k, v in packages.items():
            # First set the defaults which are not inherited from
            # the top-level, in case they are not set yet.
            v.setdefault("downstream_package_name", k)
            # Inherit default values from the top-level.
            v.update(data | v)
        data = {"packages": packages, "jobs": jobs}
        return data

    @staticmethod
    def rearrange_jobs(data: dict) -> dict:
        """Set the selected package config objects in each job, and set defaults
        according to the values specified on the level of job-objects (if any).

        Args:
            data: Configuration dict with 'packages' and 'jobs' already in place.

        Returns:
            Configuration dict where the package objects in jobs are correctly set.
        """
        packages = data["packages"]
        jobs = data["jobs"]
        errors = {}
        for i, job in enumerate(jobs):
            # Validate the 'metadata' field if there is any, and merge its
            # content with the job.
            # Do this here in order to avoid complications further in the
            # loading process.
            if metadata := job.pop("metadata", {}):
                logger.warning(
                    "The 'metadata' key in jobs is deprecated and can be removed. "
                    "Nest config options from 'metadata' directly under the job object."
                )
                schema = JobMetadataSchema()
                if errors := schema.validate(metadata):
                    raise ValidationError(errors)
                if not_nested_metadata_keys := set(schema.fields).intersection(job):
                    raise ValidationError(
                        f"Keys: {not_nested_metadata_keys} are defined outside job metadata "
                        "dictionary. Mixing obsolete metadata dictionary and new job keys "
                        "is not possible. Remove obsolete nested job metadata dictionary."
                    )
                job.update(metadata)

            top_keys = {}
            for key in JobConfigSchema().fields:
                if (value := job.pop(key, None)) is not None:
                    top_keys[key] = value

            selected_packages = top_keys.pop("packages", None)
            # Check that only packages which are defined on the top-level are selected.
            # Do this here b/c the code further down requires this to be correct.
            incorrect_packages = (
                set(selected_packages).difference(packages)
                if isinstance(selected_packages, (dict, list))
                else None
            )
            if incorrect_packages:
                errors[
                    f"jobs[{i}].packages"
                ] = f"Undefined package(s) referenced: {', '.join(incorrect_packages)}."
                continue

            # There is no 'packages' key in the job, so
            # the job should handle all the top-level packages.
            if not selected_packages:
                jobs[i] = top_keys | {
                    "packages": {k: v | job for k, v in packages.items()},
                }
            # Some top-level packages are selected to be
            # handled by the job.
            elif isinstance(selected_packages, list):
                jobs[i] = top_keys | {
                    "packages": {
                        k: v | job
                        for k, v in packages.items()
                        if k in selected_packages
                    },
                }
            # Some top-level packages are selected to be
            # handled by the job AND have some custom config.
            elif isinstance(selected_packages, dict):
                jobs[i] = top_keys | {
                    "packages": {
                        k: packages[k] | job | v for k, v in selected_packages.items()
                    },
                }
            else:
                errors[f"'jobs[{i}].packages'"] = [
                    f"Type is {type(selected_packages)} instead of 'list' or 'dict'."
                ]

        if errors:
            # This will shadow all other possible errors in the configuration,
            # as the process doesn't even get to the validation phase.
            raise ValidationError(errors)

        return data

    @post_load
    def make_instance(self, data: dict, **_) -> PackageConfig:
        return PackageConfig(**data)


class UserConfigSchema(Schema):
    """
    Schema for processing Config config data.
    """

    debug = fields.Bool()
    fas_user = fields.String()
    fas_password = fields.String()
    keytab_path = fields.String()
    redhat_api_refresh_token = fields.String()
    upstream_git_remote = fields.String()
    github_token = fields.String()
    pagure_user_token = fields.String()
    pagure_fork_token = fields.String()
    github_app_installation_id = fields.String()
    github_app_id = fields.String()
    github_app_cert_path = fields.String()
    authentication = fields.Dict()
    command_handler = fields.String()
    command_handler_work_dir = fields.String()
    command_handler_pvc_env_var = fields.String()
    command_handler_image_reference = fields.String()
    command_handler_k8s_namespace = fields.String()
    command_handler_pvc_volume_specs = fields.List(fields.Dict())
    kerberos_realm = fields.String()
    package_config_path = fields.String(default=None)
    koji_build_command = fields.String()
    pkg_tool = fields.String()
    repository_cache = fields.String(default=None)
    add_repositories_to_repository_cache = fields.Bool(default=True)

    @post_load
    def make_instance(self, data, **kwargs):
        return Config(**data)
