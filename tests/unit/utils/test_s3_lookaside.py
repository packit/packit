# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""Unit tests for S3LookasideCache."""

import os
import tempfile

import pytest

from packit.exceptions import PackitLookasideCacheException

boto3 = pytest.importorskip("boto3")
moto = pytest.importorskip("moto")

from moto import mock_aws

from packit.utils.s3_lookaside import S3LookasideCache


@pytest.fixture
def temp_file():
    """Create a temporary file with test content."""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".tar.gz", delete=False) as f:
        f.write(b"test content for lookaside cache")
        temp_path = f.name
    yield temp_path
    os.unlink(temp_path)


class TestS3LookasideCacheInit:
    def test_init_with_defaults(self):
        with mock_aws():
            boto3.client("s3", region_name="us-east-1").create_bucket(
                Bucket="test-bucket",
            )
            cache = S3LookasideCache(hashtype="sha512", bucket="test-bucket")
            assert cache.hashtype == "sha512"
            assert cache.bucket == "test-bucket"
            assert cache.prefix == ""

    def test_init_with_custom_prefix(self):
        with mock_aws():
            boto3.client("s3", region_name="us-east-1").create_bucket(
                Bucket="test-bucket",
            )
            cache = S3LookasideCache(
                hashtype="sha512", bucket="test-bucket", prefix="/sources/",
            )
            assert cache.prefix == "sources"

    def test_init_with_custom_endpoint(self):
        with mock_aws():
            cache = S3LookasideCache(
                hashtype="sha512",
                bucket="test-bucket",
                endpoint_url="http://localhost:9000",
            )
            assert cache.bucket == "test-bucket"


class TestS3LookasideCacheHashFile:
    def test_hash_file_sha512(self, temp_file):
        with mock_aws():
            boto3.client("s3", region_name="us-east-1").create_bucket(
                Bucket="test-bucket",
            )
            cache = S3LookasideCache(hashtype="sha512", bucket="test-bucket")
            file_hash = cache.hash_file(temp_file)
            assert len(file_hash) == 128
            assert all(c in "0123456789abcdef" for c in file_hash)

    def test_hash_file_sha256(self, temp_file):
        with mock_aws():
            boto3.client("s3", region_name="us-east-1").create_bucket(
                Bucket="test-bucket",
            )
            cache = S3LookasideCache(hashtype="sha512", bucket="test-bucket")
            file_hash = cache.hash_file(temp_file, hashtype="sha256")
            assert len(file_hash) == 64

    def test_hash_file_invalid_hashtype(self, temp_file):
        with mock_aws():
            boto3.client("s3", region_name="us-east-1").create_bucket(
                Bucket="test-bucket",
            )
            cache = S3LookasideCache(hashtype="sha512", bucket="test-bucket")
            with pytest.raises(
                PackitLookasideCacheException, match="Invalid hash type",
            ):
                cache.hash_file(temp_file, hashtype="invalid_hash")


class TestS3LookasideCacheUploadDownload:
    def test_upload_new_file(self, temp_file):
        with mock_aws():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="test-bucket")
            cache = S3LookasideCache(
                hashtype="sha512", bucket="test-bucket", prefix="sources",
            )
            file_hash = cache.hash_file(temp_file)

            cache.upload("rpms/test-package", temp_file, file_hash)

            assert cache.remote_file_exists(
                "rpms/test-package", os.path.basename(temp_file), file_hash,
            )

    def test_upload_existing_file_skipped(self, temp_file):
        with mock_aws():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="test-bucket")
            cache = S3LookasideCache(
                hashtype="sha512", bucket="test-bucket", prefix="sources",
            )
            file_hash = cache.hash_file(temp_file)

            cache.upload("rpms/test-package", temp_file, file_hash)
            cache.upload("rpms/test-package", temp_file, file_hash)  # Should be skipped

            assert cache.remote_file_exists(
                "rpms/test-package", os.path.basename(temp_file), file_hash,
            )

    def test_upload_offline_mode(self, temp_file):
        with mock_aws():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="test-bucket")
            cache = S3LookasideCache(
                hashtype="sha512", bucket="test-bucket", prefix="sources",
            )
            file_hash = cache.hash_file(temp_file)

            cache.upload("rpms/test-package", temp_file, file_hash, offline=True)

            assert not cache.remote_file_exists(
                "rpms/test-package", os.path.basename(temp_file), file_hash,
            )

    def test_download_file(self, temp_file):
        with mock_aws():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="test-bucket")
            cache = S3LookasideCache(
                hashtype="sha512", bucket="test-bucket", prefix="sources",
            )
            file_hash = cache.hash_file(temp_file)
            filename = os.path.basename(temp_file)

            cache.upload("rpms/test-package", temp_file, file_hash)

            with tempfile.NamedTemporaryFile(delete=False) as out_file:
                out_path = out_file.name

            try:
                cache.download("rpms/test-package", filename, file_hash, out_path)
                with open(temp_file, "rb") as f1, open(out_path, "rb") as f2:
                    assert f1.read() == f2.read()
            finally:
                os.unlink(out_path)

    def test_download_checksum_mismatch(self, temp_file):
        """Simulate file corruption by modifying content on S3 after upload."""
        with mock_aws():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="test-bucket")
            cache = S3LookasideCache(
                hashtype="sha512", bucket="test-bucket", prefix="sources",
            )
            file_hash = cache.hash_file(temp_file)
            filename = os.path.basename(temp_file)

            cache.upload("rpms/test-package", temp_file, file_hash)

            # Corrupt the file on S3
            key = cache._get_key("rpms/test-package", filename, file_hash)
            s3.put_object(Bucket="test-bucket", Key=key, Body=b"corrupted content")

            with tempfile.NamedTemporaryFile(delete=False) as out_file:
                out_path = out_file.name

            try:
                with pytest.raises(
                    PackitLookasideCacheException, match="failed checksum verification",
                ):
                    cache.download("rpms/test-package", filename, file_hash, out_path)
                assert not os.path.exists(out_path)
            finally:
                if os.path.exists(out_path):
                    os.unlink(out_path)


class TestS3LookasideCacheRemoteFileExists:
    def test_remote_file_exists_true(self, temp_file):
        with mock_aws():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="test-bucket")
            cache = S3LookasideCache(
                hashtype="sha512", bucket="test-bucket", prefix="sources",
            )
            file_hash = cache.hash_file(temp_file)
            filename = os.path.basename(temp_file)

            cache.upload("rpms/test-package", temp_file, file_hash)

            assert cache.remote_file_exists("rpms/test-package", filename, file_hash)

    def test_remote_file_exists_false(self):
        with mock_aws():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="test-bucket")
            cache = S3LookasideCache(
                hashtype="sha512", bucket="test-bucket", prefix="sources",
            )

            assert not cache.remote_file_exists(
                "rpms/test-package", "nonexistent.tar.gz", "abc123",
            )

    def test_remote_file_exists_head_compatibility(self, temp_file):
        with mock_aws():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="test-bucket")
            cache = S3LookasideCache(
                hashtype="sha512", bucket="test-bucket", prefix="sources",
            )
            file_hash = cache.hash_file(temp_file)
            filename = os.path.basename(temp_file)

            cache.upload("rpms/test-package", temp_file, file_hash)

            assert cache.remote_file_exists_head(
                "rpms/test-package", filename, file_hash, hashtype=None,
            )


class TestS3LookasideCacheGetDownloadUrl:
    def test_get_download_url(self, temp_file):
        with mock_aws():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="test-bucket")
            cache = S3LookasideCache(
                hashtype="sha512", bucket="test-bucket", prefix="sources",
            )
            file_hash = cache.hash_file(temp_file)
            filename = os.path.basename(temp_file)

            url = cache.get_download_url("rpms/test-package", filename, file_hash)

            assert "test-bucket" in url
            assert "Signature" in url or "X-Amz-Signature" in url


class TestS3LookasideCacheKeyConstruction:
    def test_key_with_prefix(self):
        with mock_aws():
            boto3.client("s3", region_name="us-east-1").create_bucket(
                Bucket="test-bucket",
            )
            cache = S3LookasideCache(
                hashtype="sha512", bucket="test-bucket", prefix="sources",
            )
            key = cache._get_key("rpms/nginx", "nginx-1.24.0.tar.gz", "abc123")
            assert (
                key
                == "sources/rpms/nginx/nginx-1.24.0.tar.gz/sha512/abc123/nginx-1.24.0.tar.gz"
            )

    def test_key_without_prefix(self):
        with mock_aws():
            boto3.client("s3", region_name="us-east-1").create_bucket(
                Bucket="test-bucket",
            )
            cache = S3LookasideCache(hashtype="sha512", bucket="test-bucket", prefix="")
            key = cache._get_key("rpms/nginx", "nginx-1.24.0.tar.gz", "abc123")
            assert (
                key
                == "rpms/nginx/nginx-1.24.0.tar.gz/sha512/abc123/nginx-1.24.0.tar.gz"
            )

    def test_key_with_custom_hashtype(self):
        with mock_aws():
            boto3.client("s3", region_name="us-east-1").create_bucket(
                Bucket="test-bucket",
            )
            cache = S3LookasideCache(
                hashtype="sha512", bucket="test-bucket", prefix="sources",
            )
            key = cache._get_key(
                "rpms/nginx", "nginx-1.24.0.tar.gz", "abc123", hashtype="sha256",
            )
            assert (
                key
                == "sources/rpms/nginx/nginx-1.24.0.tar.gz/sha256/abc123/nginx-1.24.0.tar.gz"
            )
