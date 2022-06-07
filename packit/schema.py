# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from logging import getLogger
from typing import Dict, Any, Optional, Mapping, Union, List

from marshmallow import Schema, fields, post_load, pre_load, post_dump, ValidationError
from marshmallow_enum import EnumField

from packit.actions import ActionName
from packit.config import PackageConfig, Config, CommonPackageConfig, Deployment
from packit.config.job_config import (
    JobType,
    JobConfig,
    JobConfigTriggerType,
)
from packit.config.package_config import NotificationsConfig
from packit.config.notifications import PullRequestNotificationsConfig
from packit.config.sources import SourcesItem
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
        # check the 'attributes', e.g. {'distros': ['centos-7']}
        for attr in value.values():
            for key, value in attr.items():
                if key != "distros":
                    raise ValidationError(f"Unknown key {key!r} in {attr!r}")
                if isinstance(value, list) and all(
                    isinstance(distro, str) for distro in value
                ):
                    return True
                else:
                    raise ValidationError(
                        f"Expected list[str], got {value!r} (type {type(value)!r})"
                    )
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
    enable_net = fields.Boolean(missing=True)

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
    Common methods for JobConfigSchema and PackageConfigSchema
    """

    config_file_path = fields.String(missing=None)
    specfile_path = fields.String(missing=None)
    downstream_package_name = fields.String(missing=None)
    upstream_project_url = fields.String(missing=None)
    upstream_package_name = fields.String(missing=None, validate=validate_repo_name)
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

    @staticmethod
    def spec_source_id_serialize(value: PackageConfig):
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


class JobConfigSchema(CommonConfigSchema):
    """
    Schema for processing JobConfig config data.
    """

    job = EnumField(JobType, required=True, attribute="type")
    trigger = EnumField(JobConfigTriggerType, required=True)
    # old metadata dictionary keys
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
    enable_net = fields.Boolean(missing=True)
    allowed_pr_authors = fields.List(fields.String(), missing=None)
    allowed_committers = fields.List(fields.String(), missing=None)

    metadata = fields.Nested(JobMetadataSchema)

    @pre_load
    def ordered_preprocess(self, data, **_):
        if "metadata" in data:
            logger.warning(
                "The 'metadata' key in jobs is deprecated and can be removed."
                "Nest config options from 'metadata' directly under the job object."
            )

            not_nested_metadata_keys = [
                k
                for k in (
                    "_targets",
                    "timeout",
                    "owner",
                    "project",
                    "dist_git_branches",
                    "branch",
                    "scratch",
                    "list_on_homepage",
                    "preserve_project",
                    "use_internal_tf",
                    "additional_packages",
                    "additional_repos",
                    "fmf_url",
                    "fmf_ref",
                    "skip_build",
                    "env",
                    "enable_net",
                )
                if k in data
            ]
            if not_nested_metadata_keys:
                raise ValidationError(
                    f"Keys: {not_nested_metadata_keys} are defined outside job metadata dictionary."
                    "Mixing obsolete metadata dictionary and new job keys is not possible."
                    "Remove obsolete nested job metadata dictionary."
                )

        for key in ("targets", "dist_git_branches"):
            if isinstance(data, dict) and isinstance(data.get(key), str):
                # allow key value being specified as string, convert to list
                data[key] = [data.pop(key)]

        return data

    @post_load
    def make_instance(self, data, **_):
        if "metadata" in data:
            metadata = data.pop("metadata")
            data.update(metadata)
        return JobConfig(**data)


class PackageConfigSchema(CommonConfigSchema):
    """
    Schema for processing PackageConfig config data.
    """

    jobs = fields.Nested(JobConfigSchema, many=True)

    # list of deprecated keys and their replacement (new,old)
    deprecated_keys = (("upstream_package_name", "upstream_project_name"),)

    @pre_load
    def ordered_preprocess(self, data, **kwargs):
        data = self.rename_deprecated_keys(data, **kwargs)
        data = self.add_defaults_for_jobs(data, **kwargs)
        return data

    @staticmethod
    def add_defaults_for_jobs(data, **_):
        """
        add all the fields (except for jobs) to every job so we can process only jobconfig in p-s
        """
        if not data:  # data is None when .packit.yaml is empty
            return data
        for job in data.get("jobs", []):
            for k, v in data.items():
                if k == "jobs":
                    # overriding jobs doesn't make any sense
                    continue
                job.setdefault(k, v)
        return data

    def rename_deprecated_keys(self, data, **kwargs):
        """
        Based on duples stored in tuple cls.deprecated_keys, reassigns old keys values to new keys,
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

    @post_load
    def make_instance(self, data, **kwargs):
        return PackageConfig(**data)


class UserConfigSchema(Schema):
    """
    Schema for processing Config config data.
    """

    debug = fields.Bool()
    fas_user = fields.String()
    fas_password = fields.String()
    keytab_path = fields.String()
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
