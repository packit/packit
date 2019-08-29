import os
import re
import functools
import shutil
import logging
from typing import Dict, Optional, Callable, Any
from io import BytesIO
from requests.models import Response
from requests.structures import CaseInsensitiveDict
import inspect
from enum import Enum
import datetime

from ogr.persistent_storage import PersistentObjectStorage
from ogr.utils import SingletonMeta
from packit.utils import run_command


STORAGE = PersistentObjectStorage()
STORAGE.dir_count = 0
logger = logging.getLogger(__name__)


class tempfile(metaclass=SingletonMeta):
    """
    replace system tempfile module with own predictable names implementation
     of temp files for mocking
    """

    counter = 0
    root = "/tmp"
    prefix = "static_tmp"

    @classmethod
    def _get_name(cls, prefix: Optional[str] = None) -> str:
        cls.counter += 1
        return os.path.join(cls.root, f"{prefix or cls.prefix}_{cls.counter}")

    @classmethod
    def mktemp(cls, prefix: Optional[str] = None) -> str:
        return cls._get_name(prefix)

    @classmethod
    def mkdtemp(cls, prefix: Optional[str] = None) -> str:
        name = cls._get_name(prefix)
        os.makedirs(name)
        return name


def get_if_recording() -> bool:
    """
    True if RECORD_REQUESTS env var is set, used to setup mocking
    """
    return bool(os.getenv("RECORD_REQUESTS"))


def _copy_logic(
    pers_storage: PersistentObjectStorage, source: str, destination: str
) -> None:
    """
    Internal function. Copy files to or back from persistent STORAGE location
    """
    logger.debug(f"Copy files {source} -> {destination}")
    logger.debug(f"Persistent Storage write mode: {pers_storage.is_write_mode}")
    if pers_storage.is_write_mode:
        if os.path.isdir(source):
            os.makedirs(destination)
            run_command(cmd=["cp", "-drT", source, destination])
        else:
            run_command(cmd=["cp", "-d", source, destination])
    else:
        if os.path.isdir(destination):
            if os.path.exists(source):
                shutil.rmtree(source)
            os.makedirs(source)
            run_command(cmd=["cp", "-drTf", destination, source])
        else:
            run_command(cmd=["cp", "-df", destination, source])


def store_files_return_value(func: Callable) -> Any:
    @functools.wraps(func)
    def store_files_int(*args, **kwargs):
        if not get_if_recording():
            return func(*args, **kwargs)
        else:
            data_dir = os.path.dirname(STORAGE.storage_file)
            current_dir = os.path.join(data_dir, str(STORAGE.dir_count))
            os.makedirs(data_dir, exist_ok=True)
            STORAGE.dir_count += 1
            output = store_function_output(func)(*args, **kwargs)
            _copy_logic(STORAGE, output, current_dir)
        return output

    return store_files_int


def store_files_guess_args(func: Callable) -> Any:
    @functools.wraps(func)
    def store_files_int(*args, **kwargs):
        if not get_if_recording():
            return func(*args, **kwargs)
        else:
            data_dir = os.path.dirname(STORAGE.storage_file)
            current_dir = os.path.join(data_dir, str(STORAGE.dir_count))
            os.makedirs(current_dir, exist_ok=True)
            STORAGE.dir_count += 1
            output = store_function_output(func)(*args, **kwargs)
            if STORAGE.is_write_mode:
                for position in range(len(args)):
                    arg = args[position]
                    if not isinstance(arg, str):
                        continue
                    if os.path.exists(arg):
                        current_path = os.path.join(current_dir, str(position))
                        _copy_logic(STORAGE, arg, current_path)
                for k, v in kwargs.items():
                    if os.path.exists(v):
                        current_path = os.path.join(current_dir, k)
                        _copy_logic(STORAGE, v, current_path)
            else:
                for item in os.listdir(current_dir):
                    current_path = os.path.join(current_dir, item)
                    if item.isdigit():
                        arg = args[int(item)]
                    else:
                        arg = kwargs[item]
                    _copy_logic(STORAGE, arg, current_path)
        return output

    return store_files_int


def store_files_arg_references(files_params: Dict) -> Any:
    """
    files_params = {"target_dir": 2}
    """

    def store_files_int(func):
        @functools.wraps(func)
        def store_files_int_int(*args, **kwargs):
            if not get_if_recording():
                return func(*args, **kwargs)
            else:
                data_dir = os.path.dirname(STORAGE.storage_file)
                output = store_function_output(func)(*args, **kwargs)
                for key, position in files_params.items():
                    if key in kwargs:
                        param = kwargs[key]
                    else:
                        param = args[position]
                    current_path = os.path.join(data_dir, str(STORAGE.dir_count))
                    STORAGE.dir_count += 1
                    _copy_logic(STORAGE, param, current_path)
            return output

        return store_files_int_int

    return store_files_int


def store_function_output(func: Callable) -> Any:
    @functools.wraps(func)
    def recorded_function(*args, **kwargs):
        if not get_if_recording():
            return func(*args, **kwargs)
        else:
            keys = [inspect.getmodule(func).__name__, func.__name__]
            # removed extension because using tempfiles
            # + [x for x in args if isinstance(int, str)] + [f"{k}={v}" for k, v in kwargs.items()]

            if STORAGE.is_write_mode:
                output = func(*args, **kwargs)
                STORAGE.store(keys, output)

            else:
                output = STORAGE.read(keys)
            return output

    return recorded_function


@store_function_output
def run_command_wrapper(cmd, error_message=None, cwd=None, fail=True, output=False):
    return run_command(
        cmd=cmd, error_message=error_message, cwd=cwd, fail=fail, output=output
    )


class RequestResponseHandling:
    __response_keys = ["status_code", "_content", "encoding", "reason"]
    __ignored = ["cookies"]
    __response_keys_special = ["raw", "_next", "headers", "elapsed"]
    persistent_storage = STORAGE

    def __init__(
        self, store_keys: list, pstorage: Optional[PersistentObjectStorage] = None
    ) -> None:
        self.store_keys = store_keys
        if pstorage:
            self.persistent_storage = pstorage
        self.store_keys = store_keys

    def write(self, response: Response) -> Response:
        self.persistent_storage.store(self.store_keys, self._to_dict(response))
        if getattr(response, "next"):
            self.write(getattr(response, "next"))
        return response

    def read(self):
        data = self.persistent_storage.read(self.store_keys)
        response = self._from_dict(data)
        if data["_next"]:
            response._next = self.read()
        return response

    def _to_dict(self, response: Response) -> dict:
        output = dict()
        for key in self.__response_keys:
            output[key] = getattr(response, key)
        for key in self.__response_keys_special:
            if key == "raw":
                output[key] = response.raw.read()
            if key == "headers":
                output[key] = dict(response.headers)
            if key == "elapsed":
                output[key] = response.elapsed.total_seconds()
            if key == "_next":
                output[key] = None
                if getattr(response, "next") is not None:
                    output[key] = self.store_keys
        return output

    def _from_dict(self, data: dict) -> Response:
        response = Response()
        for key in self.__response_keys:
            setattr(response, key, data[key])
        for key in self.__response_keys_special:
            if key == "raw":
                response.raw = BytesIO(data[key])
            if key == "headers":
                response.headers = CaseInsensitiveDict(data[key])
            if key == "elapsed":
                response.elapsed = datetime.timedelta(seconds=data[key])
            if key == "_next":
                setattr(response, "_next", data[key])
        return response

    @staticmethod
    def execute(keys: list, func: Callable, *args, **kwargs):
        rrstorage = RequestResponseHandling(store_keys=keys)
        if rrstorage.persistent_storage.is_write_mode:
            response = func(*args, **kwargs)
            rrstorage.write(response=response)
            return response
        else:
            response = rrstorage.read()
            return response

    @staticmethod
    def execute_all_keys(func: Callable, *args, **kwargs):
        keys = (
            [inspect.getmodule(func).__name__, func.__name__]
            + [x for x in args if isinstance(int, str)]
            + [f"{k}:{v}" for k, v in kwargs.items()]
        )
        return RequestResponseHandling.execute(keys, func, *args, **kwargs)

    @staticmethod
    def decorator(func: Callable) -> Any:
        @functools.wraps(func)
        def internal(*args, **kwargs):
            return RequestResponseHandling.execute_all_keys(func, *args, **kwargs)

        return internal

    @staticmethod
    def decorator_selected_keys(*, item_list: list) -> Any:
        def internal(func: Callable):
            @functools.wraps(func)
            def internal_internal(*args, **kwargs):
                keys = [inspect.getmodule(func).__name__, func.__name__]
                for item in item_list:
                    if isinstance(item, int):
                        keys.append(args[item])
                    else:
                        keys.append(kwargs[item])
                return RequestResponseHandling.execute(keys, func, *args, **kwargs)

            return internal_internal

        return internal


class ReplaceType(Enum):
    DECORATOR = 1
    FUNCTION = 2
    REPLACE = 3


def upgrade_import_system(
    func: Callable, name_filters: list, debug_file: Optional[str] = None
) -> Any:
    @functools.wraps(func)
    def new_import(*args, **kwargs):
        out = func(*args, **kwargs)
        name = list(args)[0]

        for filter_item in name_filters:
            one_filter = filter_item[0]
            additional_filters = filter_item[1]
            if re.search(one_filter, name):
                mod = inspect.getmodule(inspect.stack()[1][0])
                fromlist = ()
                if len(args) > 3:
                    fromlist = list(args)[3]
                module_name = getattr(mod, "__name__", "")
                module_file = getattr(mod, "__file__", "")
                item = {
                    "module_object": out,
                    "who": mod,
                    "who_name": module_name,
                    "who_filename": module_file,
                    "fromlist": fromlist,
                }

                if all([re.search(v, item[k]) for k, v in additional_filters.items()]):
                    text = list()
                    text.append(
                        f"{module_name} ({module_file})-> {name} ({fromlist})\n"
                    )
                    if len(filter_item) > 2:
                        for key, replacement in filter_item[2].items():
                            replace_type = replacement[0]
                            replace_object = replacement[1]
                            original_obj = out
                            parent_obj = out
                            # traverse into
                            if len(key) > 0:
                                for key_item in key.split("."):
                                    parent_obj = original_obj
                                    original_obj = getattr(original_obj, key_item)
                            if replace_type == ReplaceType.FUNCTION:
                                setattr(
                                    parent_obj, original_obj.__name__, replace_object
                                )
                                text.append(
                                    f"\treplacing {key} by function {replace_object.__name__}\n"
                                )
                            elif replace_type == ReplaceType.DECORATOR:
                                setattr(
                                    parent_obj,
                                    original_obj.__name__,
                                    replace_object(original_obj),
                                )
                                text.append(
                                    f"\tdecorate {key}  by {replace_object.__name__}\n"
                                )
                            elif replace_type == ReplaceType.REPLACE:
                                out = replace_object
                                text.append(
                                    f"\treplace module {module_name} by {replace_object.__name__}\n"
                                )
                    if debug_file:
                        with open(debug_file, "a") as fd:
                            fd.write("".join(text))
        return out

    return new_import
