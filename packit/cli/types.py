import click

from packit.local_project import LocalProject


class LocalProjectParameter(click.ParamType):
    """
    Path or url.
    """

    name = "repo"

    def __init__(self, branch_param_name: str = None) -> None:
        """
        :param branch_param_name: name of the cli function parameter (not the option name)
        """
        super().__init__()
        self.branch_param_name = branch_param_name

    def convert(self, value, param, ctx):
        try:
            branch_name = None
            if self.branch_param_name:
                if self.branch_param_name in ctx.params:
                    branch_name = ctx.params[self.branch_param_name]
                else:  # use the default
                    for param in ctx.command.params:
                        if param.name == self.branch_param_name:
                            branch_name = param.default

            local_project = LocalProject(path_or_url=value, ref=branch_name)
            if not local_project.working_dir and not local_project.git_url:
                self.fail(
                    "Parameter is not an existing directory nor correct git url.",
                    param,
                    ctx,
                )
            return local_project
        except Exception as ex:
            self.fail(ex, param, ctx)
