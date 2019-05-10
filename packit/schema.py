from packit.actions import ActionName


SYNCED_FILES_SCHEMA = {
    "anyOf": [
        {"type": "string"},
        {
            "type": "object",
            "properties": {
                "src": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}},
                    ]
                },
                "dest": {"type": "string"},
            },
        },
    ]
}

JOB_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "job": {
            "enum": [
                "propose_downstream",
                "build",
                "sync_from_downstream",
                "copr_build",
            ]
        },
        "trigger": {"enum": ["release", "pull_request", "commit"]},
        "notify": {"type": "array", "items": {"enum": ["pull_request_status"]}},
        "metadata": {"type": "object"},
    },
    "required": ["trigger", "job"],
}

PACKAGE_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "specfile_path": {"type": "string"},
        "downstream_package_name": {"type": "string"},
        "upstream_project_name": {"type": "string"},
        "upstream_ref": {"type": "string"},
        "create_tarball_command": {"type": "array", "items": {"type": "string"}},
        "current_version_command": {"type": "array", "items": {"type": "string"}},
        "allowed_gpg_keys": {"type": "array", "items": {"type": "string"}},
        "synced_files": {"type": "array", "items": SYNCED_FILES_SCHEMA},
        "jobs": {"type": "array", "items": JOB_CONFIG_SCHEMA},
        "actions": {
            "type": "object",
            "properties": {
                a: {"type": "string"} for a in ActionName.get_possible_values()
            },
            "additionalProperties": False,
        },
    },
    "required": ["specfile_path"],
}

USER_CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "debug": {"type": "boolean"},
        "dry_run": {"type": "boolean"},
        "fas_user": {"type": "string"},
        "keytab_path": {"type": "string"},
        "github_token": {"type": "string"},
        "pagure_user_token": {"type": "string"},
        "pagure_fork_token": {"type": "string"},
        "github_app_installation_id": {"type": "string"},
        "github_app_id": {"type": "string"},
        "github_app_cert_path": {"type": "string"},
    },
}
