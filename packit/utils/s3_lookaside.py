# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""S3-based lookaside cache implementation."""

import hashlib
import logging
import os
from pathlib import Path
from typing import Optional, Union

from packit.exceptions import PackitLookasideCacheException

logger = logging.getLogger(__name__)


class S3LookasideCache:
    """
    S3-based lookaside cache with IAM authentication.

    Provides the same interface as pyrpkg.lookaside.CGILookasideCache
    but uses S3 for storage instead of a CGI-based web server.
    """

    def __init__(
        self,
        hashtype: str,
        bucket: str,
        prefix: str = "",
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
    ):
        try:
            import boto3
            from botocore.exceptions import ClientError

            self._ClientError = ClientError
        except ImportError as e:
            raise PackitLookasideCacheException(
                "boto3 is required for S3 lookaside cache. Install with: pip install packit[s3]",
            ) from e

        self.hashtype = hashtype
        self.bucket = bucket
        self.prefix = prefix.strip("/")

        self.s3 = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
        )

    def _get_key(
        self,
        name: str,
        filename: str,
        hash: str,
        hashtype: Optional[str] = None,
    ) -> str:
        """Construct S3 key: {prefix}/{name}/{filename}/{hashtype}/{hash}/{filename}"""
        hashtype = hashtype or self.hashtype
        parts = [name, filename, hashtype, hash, filename]
        if self.prefix:
            parts.insert(0, self.prefix)
        return "/".join(parts)

    def hash_file(self, filename: Union[str, Path], hashtype: Optional[str] = None) -> str:
        """Compute hash of a local file."""
        hashtype = hashtype or self.hashtype
        try:
            h = hashlib.new(hashtype)
        except ValueError as e:
            raise PackitLookasideCacheException(f"Invalid hash type: {hashtype}") from e

        with open(filename, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def remote_file_exists(self, name: str, filename: str, hash: str) -> bool:
        """Check if a file exists in the S3 lookaside cache."""
        key = self._get_key(name, filename, hash)
        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except self._ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchKey"):
                return False
            raise PackitLookasideCacheException(
                f"Failed to check if file exists in S3: {e}",
            ) from e

    def remote_file_exists_head(
        self,
        name: str,
        filename: str,
        hash: str,
        hashtype: Optional[str],
    ) -> bool:
        """Check if file exists (pyrpkg interface compatibility)."""
        return self.remote_file_exists(name, filename, hash)

    def upload(
        self,
        name: str,
        filepath: Union[str, Path],
        hash: str,
        offline: bool = False,
    ) -> None:
        """Upload a source file to the S3 lookaside cache."""
        if offline:
            logger.info("Upload disabled (offline mode)")
            return

        filename = os.path.basename(filepath)
        key = self._get_key(name, filename, hash)

        if self.remote_file_exists(name, filename, hash):
            logger.info(f"File already exists in cache: {filename}")
            return

        logger.info(f"Uploading {filepath} to s3://{self.bucket}/{key}")

        try:
            self.s3.upload_file(
                str(filepath),
                self.bucket,
                key,
                ExtraArgs={
                    "ContentType": "application/octet-stream",
                    "Metadata": {"hashtype": self.hashtype, "hash": hash},
                },
            )
        except self._ClientError as e:
            raise PackitLookasideCacheException(
                f"Failed to upload file to S3: {e}",
            ) from e

    def download(
        self,
        name: str,
        filename: str,
        hash: str,
        outfile: Union[str, Path],
        hashtype: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Download a source file from the S3 lookaside cache."""
        hashtype = hashtype or self.hashtype
        key = self._get_key(name, filename, hash, hashtype)

        if os.path.exists(outfile):
            if self.hash_file(outfile, hashtype) == hash:
                logger.info(f"File already downloaded and verified: {outfile}")
                return

        logger.info(f"Downloading s3://{self.bucket}/{key}")

        try:
            self.s3.download_file(self.bucket, key, str(outfile))
        except self._ClientError as e:
            raise PackitLookasideCacheException(
                f"Failed to download file from S3: {e}",
            ) from e

        actual_hash = self.hash_file(outfile, hashtype)
        if actual_hash != hash:
            os.remove(outfile)
            raise PackitLookasideCacheException(
                f"{filename} failed checksum verification: expected {hash}, got {actual_hash}",
            )

    def get_download_url(
        self,
        name: str,
        filename: str,
        hash: str,
        hashtype: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Generate a presigned URL for downloading a source file."""
        key = self._get_key(name, filename, hash, hashtype)
        try:
            return self.s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=3600,
            )
        except self._ClientError as e:
            raise PackitLookasideCacheException(
                f"Failed to generate presigned URL: {e}",
            ) from e
