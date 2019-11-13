import subprocess


def call_real_packit(parameters=None, envs=None, cwd=None):
    """ invoke packit in a subprocess """
    cmd = ["python3", "-m", "packit.cli.packit_base"] + parameters
    return subprocess.check_call(cmd, env=envs, cwd=cwd)


def call_real_packit_and_return_exit_code(parameters=None, envs=None, cwd=None):
    """ invoke packit in a subprocess and return exit code"""
    cmd = ["python3", "-m", "packit.cli.packit_base"] + parameters
    return subprocess.call(cmd, env=envs, cwd=cwd)
