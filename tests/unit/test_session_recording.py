import os
import sys
import unittest
import importlib
import builtins

import tempfile
import shutil
from packit import session_recording
from ogr.persistent_storage import PersistentObjectStorage

os.environ["RECORD_REQUESTS"] = "TRUE"


class Base(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.file_name = None
        self.temp_dir = None
        self.temp_file = None
        self.response_dir = tempfile.mkdtemp(prefix="data_store")
        self.response_file = os.path.join(self.response_dir, "storage_test.yaml")
        PersistentObjectStorage().storage_file = self.response_file
        PersistentObjectStorage().dump_after_store = True
        PersistentObjectStorage()._is_write_mode = True
        PersistentObjectStorage().dir_count = 0

    def tearDown(self) -> None:
        pass
        super().tearDown()
        shutil.rmtree(self.response_dir)
        if self.file_name:
            os.remove(self.file_name)
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if self.temp_file and os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def create_temp_dir(self):
        if self.temp_dir:
            shutil.rmtree(self.temp_dir)
        self.temp_dir = tempfile.mkdtemp()

    def create_temp_file(self):
        if self.temp_file:
            os.remove(self.temp_file)
        self.temp_file = tempfile.mktemp()

    @session_recording.store_files_arg_references({"target_file": 2})
    def create_file_content(self, value, target_file):
        with open(target_file, "w") as fd:
            fd.write(value)
        return "value"

    @session_recording.store_files_arg_references({"target_dir": 2})
    def create_dir_content(self, filename, target_dir, content="empty"):
        with open(os.path.join(target_dir, filename), "w") as fd:
            fd.write(content)


class SessionRecording(Base):
    def test_run_command_true(self):
        """
        Test if session recording is able to store and return output
        from command via decorating run_command
        """
        output = session_recording.run_command_wrapper(cmd=["true"])
        self.assertTrue(output)
        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False
        before = str(PersistentObjectStorage().storage_object)
        output = session_recording.run_command_wrapper(cmd=["true"])
        after = str(PersistentObjectStorage().storage_object)
        self.assertTrue(output)
        self.assertIn("True", before)
        self.assertNotIn("True", after)
        self.assertGreater(len(before), len(after))

    def test_run_command_output(self):
        """
         check if wrapper returns proper string values in calls
        """
        self.file_name = tempfile.mktemp()
        with open(self.file_name, "w") as fd:
            fd.write("ahoj\n")
        output = session_recording.run_command_wrapper(
            cmd=["cat", self.file_name], output=True
        )
        self.assertIn("ahoj", output)
        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False
        with open(self.file_name, "a") as fd:
            fd.write("cao\n")
        output = session_recording.run_command_wrapper(
            cmd=["cat", self.file_name], output=True
        )
        self.assertIn("ahoj", output)
        self.assertNotIn("cao", output)
        PersistentObjectStorage()._is_write_mode = True
        output = session_recording.run_command_wrapper(
            cmd=["cat", self.file_name], output=True
        )
        self.assertIn("cao", output)
        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False
        output = session_recording.run_command_wrapper(
            cmd=["cat", self.file_name], output=True
        )
        self.assertIn("cao", output)


class FileStorage(SessionRecording):
    def test_create_file_content(self):
        """
        test if is able store files via decorated function create_file_content
        """
        self.assertEqual(PersistentObjectStorage().dir_count, 0)
        self.create_temp_file()
        self.assertEqual(
            "value", self.create_file_content("ahoj", target_file=self.temp_file)
        )

        self.assertEqual(PersistentObjectStorage().dir_count, 1)
        self.create_file_content("cao", target_file=self.temp_file)
        self.assertEqual(PersistentObjectStorage().dir_count, 2)

        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False
        PersistentObjectStorage().dir_count = 0

        self.create_file_content("first", target_file=self.temp_file)
        with open(self.temp_file, "r") as fd:
            content = fd.read()
            self.assertIn("ahoj", content)
            self.assertNotIn("cao", content)
        self.create_file_content("second", target_file=self.temp_file)
        with open(self.temp_file, "r") as fd:
            content = fd.read()
            self.assertNotIn("ahoj", content)
            self.assertIn("cao", content)
        self.assertRaises(
            Exception, self.create_file_content, "third", target_file=self.temp_file
        )

    def test_create_file_content_positional(self):
        """
        Similar to  test_create_file_content,
        but test it also via positional parameters and mixing them
        """
        self.assertEqual(PersistentObjectStorage().dir_count, 0)
        self.create_temp_file()
        self.create_file_content("ahoj", self.temp_file)
        self.assertEqual(PersistentObjectStorage().dir_count, 1)
        self.create_file_content("cao", self.temp_file)
        self.assertEqual(PersistentObjectStorage().dir_count, 2)

        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False
        PersistentObjectStorage().dir_count = 0

        self.create_temp_file()
        self.create_file_content("first", self.temp_file)
        with open(self.temp_file, "r") as fd:
            content = fd.read()
            self.assertIn("ahoj", content)
            self.assertNotIn("cao", content)
        # mix with positional option

        self.create_temp_file()
        self.create_file_content("second", target_file=self.temp_file)
        with open(self.temp_file, "r") as fd:
            content = fd.read()
            self.assertNotIn("ahoj", content)
            self.assertIn("cao", content)
        self.create_temp_file()
        self.assertRaises(
            Exception, self.create_file_content, "third", target_file=self.temp_file
        )

    def test_create_dir_content(self):
        """
        Check if properly store and restore directory content
        """
        self.assertEqual(PersistentObjectStorage().dir_count, 0)
        self.create_temp_dir()
        self.create_dir_content(
            filename="ahoj", target_dir=self.temp_dir, content="ciao"
        )
        self.assertEqual(PersistentObjectStorage().dir_count, 1)
        self.assertIn("ahoj", os.listdir(self.temp_dir))
        with open(os.path.join(self.temp_dir, "ahoj"), "r") as fd:
            content = fd.read()
            self.assertIn("ciao", content)

        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False
        PersistentObjectStorage().dir_count = 0

        self.create_temp_dir()
        self.create_dir_content(
            filename="nonsense", target_dir=self.temp_dir, content="bad"
        )
        self.assertIn("ahoj", os.listdir(self.temp_dir))
        self.assertNotIn("nonsense", os.listdir(self.temp_dir))
        with open(os.path.join(self.temp_dir, "ahoj"), "r") as fd:
            content = fd.read()
            self.assertIn("ciao", content)
            self.assertNotIn("bad", content)


class SessionRecordingWithFileStore(Base):
    @session_recording.store_files_arg_references({"target_file": 2})
    def create_file_content(self, value, target_file):
        session_recording.run_command_wrapper(
            cmd=["bash", "-c", f"echo {value} > {target_file}"]
        )
        with open(target_file, "w") as fd:
            fd.write(value)

    def test(self):
        """
        Mixing command wrapper with file storage
        """
        self.assertEqual(PersistentObjectStorage().dir_count, 0)
        self.create_temp_file()
        self.create_file_content("ahoj", target_file=self.temp_file)
        self.assertEqual(PersistentObjectStorage().dir_count, 1)
        self.create_file_content("cao", target_file=self.temp_file)
        self.assertEqual(PersistentObjectStorage().dir_count, 2)

        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False
        PersistentObjectStorage().dir_count = 0
        before = str(PersistentObjectStorage().storage_object)

        self.create_file_content("ahoj", target_file=self.temp_file)
        with open(self.temp_file, "r") as fd:
            content = fd.read()
            self.assertIn("ahoj", content)
            self.assertNotIn("cao", content)
        self.create_file_content("cao", target_file=self.temp_file)
        with open(self.temp_file, "r") as fd:
            content = fd.read()
            self.assertNotIn("ahoj", content)
            self.assertIn("cao", content)
        after = str(PersistentObjectStorage().storage_object)
        self.assertGreater(len(before), len(after))
        self.assertIn("True", before)


class DynamicFileStorage(Base):
    @session_recording.store_files_guess_args
    def create_file(self, value, target_file):
        with open(target_file, "w") as fd:
            fd.write(value)

    def test_create_file(self):
        """
        File storage where it try to guess what to store, based on *args and **kwargs values
        """
        self.assertEqual(PersistentObjectStorage().dir_count, 0)
        self.create_temp_file()
        self.create_file("ahoj", self.temp_file)
        self.assertEqual(PersistentObjectStorage().dir_count, 1)
        self.create_file("cao", self.temp_file)
        self.assertEqual(PersistentObjectStorage().dir_count, 2)

        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False
        PersistentObjectStorage().dir_count = 0
        self.create_temp_file()
        self.create_file("first", self.temp_file)
        with open(self.temp_file, "r") as fd:
            content = fd.read()
            self.assertIn("ahoj", content)
            self.assertNotIn("cao", content)
        # mix with positional option

        self.create_temp_file()
        self.create_file("second", self.temp_file)
        with open(self.temp_file, "r") as fd:
            content = fd.read()
            self.assertNotIn("ahoj", content)
            self.assertIn("cao", content)
        self.create_temp_file()
        self.assertRaises(
            Exception, self.create_file_content, "third", target_file=self.temp_file
        )


class StoreOutputFile(Base):
    @session_recording.store_files_return_value
    def create_file(self, value):
        tmpfile = tempfile.mktemp()
        with open(tmpfile, "w") as fd:
            fd.write(value)
        return tmpfile

    def test_create_file(self):
        """
        Test File storage if file name is return value of function
        """
        self.assertEqual(PersistentObjectStorage().dir_count, 0)
        ofile1 = self.create_file("ahoj")
        self.assertEqual(PersistentObjectStorage().dir_count, 1)
        ofile2 = self.create_file("cao")
        self.assertEqual(PersistentObjectStorage().dir_count, 2)

        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False
        PersistentObjectStorage().dir_count = 0

        oofile1 = self.create_file("first")
        with open(ofile1, "r") as fd:
            content = fd.read()
            self.assertIn("ahoj", content)
            self.assertNotIn("cao", content)
        with open(oofile1, "r") as fd:
            content = fd.read()
            self.assertIn("ahoj", content)
            self.assertNotIn("cao", content)
        # mix with positional option

        oofile2 = self.create_file("second")
        with open(oofile2, "r") as fd:
            content = fd.read()
            self.assertNotIn("ahoj", content)
            self.assertIn("cao", content)
        self.assertEqual(ofile2, oofile2)


class StoreAnyRequest(Base):
    domain = "https://example.com/"

    def setUp(self) -> None:
        super().setUp()
        self.requests = importlib.import_module("requests")
        self.post_orig = getattr(self.requests, "post")

    def tearDown(self) -> None:
        super().tearDown()
        setattr(self.requests, "post", self.post_orig)

    def testRawCall(self):
        """
        Test if is class is able to explicitly write and read request handling
        """
        keys = [self.domain]
        sess = session_recording.RequestResponseHandling(store_keys=keys)
        response = self.requests.post(*keys)
        sess.write(response)

        response_after = sess.read()
        self.assertIsInstance(response_after, self.requests.models.Response)
        self.assertNotIn("Example Domain", str(sess.persistent_storage.storage_object))
        self.assertIn("Example Domain", response_after.text)

    def testExecuteWrapper(self):
        """
        test if it is able to use explicit decorator for storing request handling
        :return:
        """
        response_before = session_recording.RequestResponseHandling.execute_all_keys(
            self.requests.post, self.domain
        )
        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False
        response_after = session_recording.RequestResponseHandling.execute_all_keys(
            self.requests.post, self.domain
        )
        self.assertEqual(response_before.text, response_after.text)
        self.assertRaises(
            Exception,
            session_recording.RequestResponseHandling.execute_all_keys,
            self.requests.post,
            self.domain,
        )

    def testFunctionDecorator(self):
        """
        Test main purpose of the class, decorate post function and use it then
        """
        self.requests.post = session_recording.RequestResponseHandling.decorator(
            self.requests.post
        )
        response_before = self.requests.post(self.domain)
        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False

        response_after = self.requests.post(self.domain)
        self.assertEqual(response_before.text, response_after.text)
        self.assertRaises(Exception, self.requests.post, self.domain)

    def testFunctionDecoratorNotFound(self):
        """
        Check if it fails with Exception in case request is not stored
        """
        self.requests.post = session_recording.RequestResponseHandling.decorator(
            self.requests.post
        )
        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False
        self.assertRaises(Exception, self.requests.post, self.domain, data={"a": "b"})

    def testFunctionCustomFields(self):
        """
        Test if it is able to use partial storing of args, kwargs
        prepare to avoid leak authentication to data
        """
        self.requests.post = session_recording.RequestResponseHandling.decorator_selected_keys(
            self.requests.post, [0]
        )
        response_before = self.requests.post(self.domain)
        response_google_before = self.requests.post(
            "http://www.google.com", data={"a": "b"}
        )
        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False

        response_after = self.requests.post(self.domain)
        response_google_after = self.requests.post("http://www.google.com")
        self.assertEqual(response_before.text, response_after.text)
        self.assertEqual(response_google_before.text, response_google_after.text)
        self.assertRaises(Exception, self.requests.post, self.domain)

    def testFunctionCustomFieldsWrong(self):
        """
        Check exceptions if using partial keys storing
        """
        self.requests.post = session_recording.RequestResponseHandling.decorator_selected_keys(
            self.requests.post, [0, "data"]
        )
        self.requests.post(self.domain, data={"a": "b"})
        response_2 = self.requests.post(self.domain, data={"c": "d"})
        PersistentObjectStorage().dump()
        PersistentObjectStorage()._is_write_mode = False

        self.assertRaises(Exception, self.requests.post, self.domain, data={"x": "y"})
        self.assertRaises(KeyError, self.requests.post, self.domain)
        response_2_after = self.requests.post(self.domain, data={"c": "d"})
        self.assertEqual(response_2.text, response_2_after.text)


class TestUpgradeImportSystem(unittest.TestCase):
    def tearDown(self) -> None:
        if "tempfile" in sys.modules:
            del sys.modules["tempfile"]
        super().tearDown()

    def testImport(self):
        """
        Test improving of import system with import statement
        Check also debug file output if it contains proper debug data
        """
        debug_file = "__modules.log"
        HANDLE_MODULE_LIST = [
            (
                "^tempfile$",
                {"who_name": "test_session_recording"},
                {"mktemp": [session_recording.ReplaceType.FUNCTION, lambda: "a"]},
            )
        ]
        builtins.__import__ = session_recording.upgrade_import_system(
            builtins.__import__, name_filters=HANDLE_MODULE_LIST, debug_file=debug_file
        )
        import tempfile

        self.assertNotIn("/tmp", tempfile.mktemp())
        self.assertIn("a", tempfile.mktemp())
        with open(debug_file, "r") as fd:
            output = fd.read()
            self.assertIn("tests.unit.test_session_recording", output)
            self.assertIn("replacing mktemp by function", output)
        os.remove(debug_file)

    def testImportFrom(self):
        """
        Test if it able to patch also from statement
        """
        HANDLE_MODULE_LIST = [
            (
                "^tempfile$",
                {"who_name": "test_session_recording"},
                {"mktemp": [session_recording.ReplaceType.FUNCTION, lambda: "b"]},
            )
        ]
        builtins.__import__ = session_recording.upgrade_import_system(
            builtins.__import__, name_filters=HANDLE_MODULE_LIST
        )
        from tempfile import mktemp

        self.assertNotIn("/tmp", mktemp())
        self.assertIn("b", mktemp())

    def testImportDecorator(self):
        """
        Test patching by decorator, not replacing whole function
        """
        HANDLE_MODULE_LIST = [
            (
                "^tempfile$",
                {"who_name": "test_session_recording"},
                {
                    "mktemp": [
                        session_recording.ReplaceType.DECORATOR,
                        lambda x: lambda: f"decorated {x()}",
                    ]
                },
            )
        ]
        builtins.__import__ = session_recording.upgrade_import_system(
            builtins.__import__, name_filters=HANDLE_MODULE_LIST
        )
        import tempfile

        self.assertIn("decorated", tempfile.mktemp())
        self.assertIn("/tmp", tempfile.mktemp())

    def testImportReplaceModule(self):
        """
        Test if it is able to replace whole module by own implemetation
        Test also own implementation of static tempfile module via class
        """

        HANDLE_MODULE_LIST = [
            (
                "^tempfile$",
                {"who_name": "test_session_recording"},
                {
                    "mktemp": [
                        session_recording.ReplaceType.REPLACE,
                        session_recording.tempfile,
                    ]
                },
            )
        ]
        builtins.__import__ = session_recording.upgrade_import_system(
            builtins.__import__, name_filters=HANDLE_MODULE_LIST
        )
        import tempfile

        tmpfile = tempfile.mktemp()
        tmpdir = tempfile.mkdtemp()
        self.assertIn("/tmp/static_tmp", tmpfile)
        self.assertIn("/tmp/static_tmp", tmpdir)
        self.assertFalse(os.path.exists(tmpfile))
        self.assertTrue(os.path.exists(tmpdir))
        self.assertTrue(os.path.isdir(tmpdir))
        os.removedirs(tmpdir)
