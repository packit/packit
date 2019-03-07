"""
A book with our finest spells
"""
import subprocess


def git_set_user_email(directory):
    subprocess.check_call(["git", "config", "user.email", "test@example.com"], cwd=directory)
    subprocess.check_call(["git", "config", "user.name", "Packit Test Suite"], cwd=directory)
