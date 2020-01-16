import logging
import typing

from marshmallow import Schema, fields, post_load, pre_load, ValidationError
from marshmallow_enum import EnumField

from packit.actions import ActionName
from packit.config import PackageConfig, Config, SyncFilesConfig
from packit.config.job_config import JobType, JobTriggerType, JobConfig, default_jobs
from packit.sync import SyncFilesItem

logger = logging.getLogger(__name__)


class FilesToSyncField(fields.Field):
    """
    Field class representing SyncFilesItem.
    Accepts str or dict  {'src': str, 'dest':str}
    """

    def _serialize(self, value: typing.Any, attr: str, obj: typing.Any, **kwargs):
        raise NotImplementedError

    def _deserialize(
        self,
        value: typing.Any,
        attr: typing.Optional[str],
        data: typing.Optional[typing.Mapping[str, typing.Any]],
        **kwargs,
    ) -> SyncFilesItem:
        if isinstance(value, dict):
            try:
                if not isinstance(value["src"], str):
                    raise ValidationError("src have to be str")
                if not isinstance(value["dest"], str):
                    raise ValidationError("dest have to be str")
                file_to_sync = SyncFilesItem(src=value["src"], dest=value["dest"])
            except KeyError as e:
                raise ValidationError(e.__repr__())

        elif isinstance(value, str):
            file_to_sync = SyncFilesItem(src=value, dest=value)

        else:
            raise ValidationError("Invalid data provided. str/dict required")

        return file_to_sync


class ActionField(fields.Field):
    """
    Field class representing Action.
    """

    def _serialize(self, value: typing.Any, attr: str, obj: typing.Any, **kwargs):
        raise NotImplementedError

    def _deserialize(
        self,
        value: typing.Any,
        attr: typing.Optional[str],
        data: typing.Optional[typing.Mapping[ActionName, typing.Any]],
        **kwargs,
    ) -> typing.Dict:
        if not isinstance(value, dict):
            raise ValidationError("Invalid data provided. dict required")

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
    Field class to mark fields which wil not be processed, only generates warning.
    Can be passed additional message via additional_message parameter.

    :param str additional_message: additional warning message to be displayed
    """

    def _serialize(self, value: typing.Any, attr: str, obj: typing.Any, **kwargs):
        raise NotImplementedError

    def _deserialize(
        self,
        value: typing.Any,
        attr: typing.Optional[str],
        data: typing.Optional[typing.Mapping[str, typing.Any]],
        **kwargs,
    ):
        logger.warning(f"{self.name} is no longer being processed.")
        additional_message = self.metadata.get("additional_message")
        if additional_message:
            logger.warning(f"{additional_message}")


class SyncFilesConfigSchema(Schema):
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


class JobConfigSchema(Schema):
    """
    Schema for processing JobConfig config data.
    """

    job = EnumField(JobType, required=True)
    trigger = EnumField(JobTriggerType, required=True)
    metadata = fields.Dict(missing={})

    @post_load
    def make_instance(self, data, **kwargs):
        return JobConfig(**data)


class PackageConfigSchema(Schema):
    """
    Schema for processing PackageConfig config data.
    """

    config_file_path = fields.String()
    specfile_path = fields.String(required=True)
    downstream_package_name = fields.String()
    upstream_project_url = fields.String(missing=None)
    upstream_package_name = fields.String()
    upstream_ref = fields.String()
    upstream_tag_template = fields.String()
    dist_git_url = NotProcessedField(
        additional_message="it is generated from dist_git_base_url and downstream_package_name"
    )
    dist_git_base_url = fields.String()
    dist_git_namespace = fields.String()
    create_tarball_command = fields.List(fields.String())
    current_version_command = fields.List(fields.String())
    allowed_gpg_keys = fields.List(fields.String())
    spec_source_id = fields.Method(deserialize="spec_source_id_fm")
    synced_files = fields.Nested(SyncFilesConfigSchema)
    jobs = fields.Nested(JobConfigSchema, many=True, default=default_jobs)
    actions = ActionField(default={})
    create_pr = fields.Bool(default=True)
    patch_generation_ignore_paths = fields.List(fields.String())

    # list of deprecated keys and their replacement (new,old)
    deprecated_keys = (("upstream_package_name", "upstream_project_name"),)

    @pre_load
    def ordered_preprocess(self, data, **kwargs):
        data = self.rename_deprecated_keys(data, **kwargs)
        data = self.specfile_path_pre(data, **kwargs)
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
                    f" please update your configuration file"
                )
                new_key_value = data.get(new_key_name, None)
                if not new_key_value:
                    # prio: new > old
                    data[new_key_name] = old_key_value
                del data[old_key_name]
        return data

    def specfile_path_pre(self, data, **kwargs):
        """
        Method for pre-processing specfile_path value. If is None, will try to generate from,
        donwstream_package_name, else will keep None and generate warning.

        :param data: conf dictionary to process
        :return: processed dictionary
        """

        specfile_path = data.get("specfile_path", None)
        if not specfile_path:
            downstream_package_name = data.get("downstream_package_name", None)
            if downstream_package_name:
                data["specfile_path"] = f"{downstream_package_name}.spec"
                logger.info(f"We guess that spec file is at {specfile_path}")
            else:
                # guess it?
                logger.warning("Path to spec file is not set.")
        return data

    @post_load
    def make_instance(self, data, **kwargs):
        return PackageConfig(**data)

    def spec_source_id_fm(self, value):
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


class UserConfigSchema(Schema):
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
