# MIT License
#
# Copyright (c) 2018-2019 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from logging import getLogger
from typing import Dict, Any, Optional, Mapping, Union

from marshmallow import Schema, fields, post_load, pre_load, ValidationError, post_dump

try:
    from marshmallow import __version_info__

    MM3 = __version_info__[0] >= 3
except ImportError:
    MM3 = False
from marshmallow_enum import EnumField

from packit.actions import ActionName
from packit.config import PackageConfig, Config, SyncFilesConfig
from packit.config.job_config import (
    JobType,
    JobConfig,
    JobConfigTriggerType,
    JobMetadataConfig,
)
from packit.config.package_config import NotificationsConfig
from packit.config.notifications import PullRequestNotificationsConfig
from packit.sync import SyncFilesItem

logger = getLogger(__name__)


class FilesToSyncField(fields.Field):
    """
    Field class representing SyncFilesItem.
    Accepts str or dict  {'src': str, 'dest':str}
    """

    def _serialize(self, value: Any, attr: str, obj: Any, **kwargs):
        return {"src": value.src, "dest": value.dest}

    def _deserialize(
        self,
        value: Any,
        attr: Optional[str],
        data: Optional[Mapping[str, Any]],
        **kwargs,
    ) -> SyncFilesItem:
        if isinstance(value, dict):
            try:
                if not isinstance(value["src"], str):
                    raise ValidationError("Field `src` should have type str.")
                if not isinstance(value["dest"], str):
                    raise ValidationError("Field `dest` should have type str.")
                file_to_sync = SyncFilesItem(src=value["src"], dest=value["dest"])
            except KeyError as e:
                raise ValidationError(e.__repr__())

        elif isinstance(value, str):
            file_to_sync = SyncFilesItem(src=value, dest=value)

        else:
            raise ValidationError(f"'dict' or 'str' required, got {type(value)!r}.")

        return file_to_sync


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
        data: Optional[Mapping[ActionName, Any]],
        **kwargs,
    ) -> Dict:
        if not isinstance(value, dict):
            raise ValidationError(f"'dict' required, got {type(value)!r}.")

        self.validate_all_actions(actions=list(value))
        data = {ActionName(key): val for key, val in value.items()}
        return data

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


class MM23Schema(Schema):
    """
    Schema compatible with Marshmallow v2 and v3.
    Remove this once we don't need v2 (when F31 is EOL) and inherit directly from Schema.
    """

    def __init__(self, **kwargs):
        if MM3:
            super().__init__(**kwargs)
        else:  # v2
            super().__init__(strict=True, **kwargs)

    def load_config(self, *args, **kwargs):
        if MM3:
            result = super().load(*args, **kwargs)
        else:  # v2
            result = super().load(*args, **kwargs).data
        return result

    def dump_config(self, *args, **kwargs):
        if MM3:
            result = super().dump(*args, **kwargs)
        else:  # v2
            result = super().dump(*args, **kwargs).data
        return result

    @post_dump
    def remove_none_values(self, data, **kwargs):
        return {key: value for key, value in data.items() if value is not None}


class PullRequestNotificationsSchema(MM23Schema):
    """ Configuration of commenting on pull requests. """

    successful_build = fields.Bool(default=True)

    @post_load
    def make_instance(self, data, **kwargs):
        return PullRequestNotificationsConfig(**data)


class NotificationsSchema(MM23Schema):
    """ Configuration of notifications. """

    pull_request = fields.Nested(PullRequestNotificationsSchema)

    @post_load
    def make_instance(self, data, **kwargs):
        return NotificationsConfig(**data)


class SyncFilesConfigSchema(MM23Schema):
    """
    Schema for processing SyncFilesConfig config data.
    """

    files_to_sync = fields.List(FilesToSyncField(allow_none=False), allow_none=True)

    @post_load
    def make_instance(self, data, **kwargs):
        return SyncFilesConfig(**data)

    @pre_load
    def list_to_dict(self, data, **kwargs):
        """
        If files are provided as list[str] not as schema dict, input data format is modified
        to follow schema layout

        ex.
        [f1,f2,..] -> {"files_to_sync": [f1, f2, f3, ...]}
        """

        if isinstance(data, list):
            return {"files_to_sync": data}
        else:
            return data


class JobMetadataSchema(MM23Schema):
    """ Jobs metadata. """

    targets = fields.List(fields.String())
    timeout = fields.Integer()
    owner = fields.String()
    project = fields.String()
    dist_git_branches = fields.List(fields.String())
    branch = fields.String()
    scratch = fields.Boolean()

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

    @post_load
    def make_instance(self, data, **_):
        return JobMetadataConfig(**data)


class CommonConfigSchema(MM23Schema):
    """
    Common methods for JobConfigSchema and PackageConfigSchema
    """

    config_file_path = fields.String()
    specfile_path = fields.String()
    downstream_package_name = fields.String()
    upstream_project_url = fields.String(missing=None)
    upstream_package_name = fields.String()
    upstream_ref = fields.String()
    upstream_tag_template = fields.String()
    dist_git_url = NotProcessedField(
        additional_message="it is generated from dist_git_base_url and downstream_package_name",
        load_only=True,
    )
    dist_git_base_url = fields.String()
    dist_git_namespace = fields.String()
    create_tarball_command = fields.List(fields.String())
    current_version_command = fields.List(fields.String())
    allowed_gpg_keys = fields.List(fields.String())
    spec_source_id = fields.Method(
        deserialize="spec_source_id_fm", serialize="spec_source_id_serialize"
    )
    synced_files = fields.Nested(SyncFilesConfigSchema)
    actions = ActionField(default={})
    create_pr = fields.Bool(default=True)
    patch_generation_ignore_paths = fields.List(fields.String())
    notifications = fields.Nested(NotificationsSchema)

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


class JobConfigSchema(CommonConfigSchema):
    """
    Schema for processing JobConfig config data.
    """

    job = EnumField(JobType, required=True, attribute="type")
    trigger = EnumField(JobConfigTriggerType, required=True)
    metadata = fields.Nested(JobMetadataSchema)

    @post_load
    def make_instance(self, data, **_):
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
        data = self.specfile_path_pre(data, **kwargs)
        data = self.add_defaults_for_jobs(data, **kwargs)
        return data

    @staticmethod
    def add_defaults_for_jobs(data, **_):
        """
        add all the fields (except for jobs) to every job so we can process only jobconfig in p-s
        """
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

    def specfile_path_pre(self, data: Dict, **kwargs):
        """
        Method for pre-processing specfile_path value.
        Set it to downstream_package_name if specified, else leave unset.

        :param data: conf dictionary to process
        :return: processed dictionary
        """

        specfile_path = data.get("specfile_path", None)
        if not specfile_path:
            downstream_package_name = data.get("downstream_package_name", None)
            if downstream_package_name:
                data["specfile_path"] = f"{downstream_package_name}.spec"
                logger.debug(
                    f'Setting `specfile_path` to "./{downstream_package_name}.spec".'
                )
            else:
                # guess it?
                logger.debug(
                    "Neither `specfile_path` nor `downstream_package_name` set."
                )
        return data

    @post_load
    def make_instance(self, data, **kwargs):
        return PackageConfig(**data)


class UserConfigSchema(MM23Schema):
    """
    Schema for processing Config config data.
    """

    debug = fields.Bool()
    dry_run = fields.Bool()
    fas_user = fields.String()
    keytab_path = fields.String()
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

    @post_load
    def make_instance(self, data, **kwargs):
        return Config(**data)
