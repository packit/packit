#!/usr/bin/python3
from packit.local_project import LocalProject

assert LocalProject(full_name="namespace/repository_name")

print("Success", LocalProject)
