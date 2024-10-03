# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Code that backs up Image Builder integration.

Guides and more info about Image Builder:
    https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/composing_a_customized_rhel_system_image/index
    https://www.redhat.com/en/blog/using-hosted-image-builder-its-api
    https://github.com/packit/research/tree/main/image-builder
"""
import logging
from typing import Optional, Union

import requests
from requests import HTTPError

from packit.exceptions import ImageBuilderError, PackitException

logger = logging.getLogger("packit")
REDHAT_SSO_AUTH_URL = (
    "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token"
)
REDHAT_API_GET_USER_URL = "https://api.access.redhat.com/account/v1/user"
API_ROOT = "https://console.redhat.com/api/"
IMAGE_BUILDER_API_URL = f"{API_ROOT}image-builder/v1"
LAUNCH_API_URL = f"{API_ROOT}provisioning/v1"


class ImageBuilder:
    """
    Client class to work with Image Builder API and Red Hat SSO.
    """

    def __init__(
        self,
        refresh_token: str,
    ):
        """
        Args:
            refresh_token: your personal token to access Red Hat SSO, obtain at:
                https://access.redhat.com/management/api
        """
        self.refresh_token = refresh_token
        self._access_token: Optional[str] = None

        self.session = requests.Session()
        self.refresh_auth()

    def refresh_auth(self):
        """
        Refresh the access token and the image_builder_session headers.
        """
        self._access_token = self._get_access_token()
        if not self._access_token:
            raise PackitException(
                "Unable to obtain access token. You may need to regenerate the refresh token.",
            )
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self._access_token}",
                "Accept": "application/json",
            },
        )

    def request(self, method: str, url: str, payload: Optional[dict] = None):
        """
        Request to the Image Builder API.

        Args:
            method: HTTP method to use (GET, POST, PUT, DELETE)
            url: complete URL for the request
            payload: payload to send with the request

        Returns:
            requests.Response object.
        """
        # don't try to refresh twice
        token_is_fresh = False
        while True:
            response = self.session.request(method, url, json=payload)
            if response.status_code == 401 and not token_is_fresh:
                token_is_fresh = True
                self.refresh_auth()
                continue
            try:
                response.raise_for_status()
            except HTTPError as ex:
                logger.error(f"Image Builder Errors: {response.text}")
                raise ImageBuilderError(errors=response.text) from ex
            return response

    def image_builder_request(
        self,
        method: str,
        path: str,
        payload: Optional[dict] = None,
    ):
        """
        Request to the Image Builder API.

        Args:
            method: HTTP method to use (GET, POST, PUT, DELETE)
            path: path part in the URL to the API endpoint
            payload: payload to send with the request

        Returns:
            requests.Response object.
        """
        return self.request(
            method,
            url=f"{IMAGE_BUILDER_API_URL}/{path}",
            payload=payload,
        )

    def launch_request(self, method: str, path: str, payload: Optional[dict] = None):
        """
        Request to the Launch API.

        Args:
            method: HTTP method to use (GET, POST, PUT, DELETE)
            path: path part in the URL to the API endpoint
            payload: payload to send with the request

        Returns:
            requests.Response object.
        """
        return self.request(method, url=f"{LAUNCH_API_URL}/{path}", payload=payload)

    def _get_access_token(self) -> Optional[str]:
        """
        Obtain access token from Red Hat SSO using the provided refresh token.

            curl -X POST -d grant_type=refresh_token \
              -d client_id=rhsm-api -d refresh_token=$o \
              https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token

        Returns:
            access token (used for interacting with the API)
        """
        sso = requests.Session()
        response = sso.post(
            REDHAT_SSO_AUTH_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": "rhsm-api",
                "refresh_token": self.refresh_token,
            },
        )
        response_json = response.json()
        try:
            return response_json["access_token"]
        except KeyError:
            logger.info(
                f"Failed to get access token ({response.status_code}): {response_json}",
            )
            return None

    def check_token(self) -> dict:
        """
        Using the obtained access token, check that it is valid by obtaining the
        user info.

        Returns:
            Dict payload with the user info.
        """
        response = requests.get(
            REDHAT_API_GET_USER_URL,
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        return response.json()

    def create_image(
        self,
        image_distribution: str,
        image_name: str,
        image_request: dict,
        image_customizations: dict,
        repo_url: Optional[str] = None,
    ):
        """
        Create an image using the Image Builder API.
        Images are called a compose in context of Image Builder.

        request and customization fields are passed to Image Builder, see
        their API for the definition, example:

          "customizations": {
            "filesystem": [
              {
                "min_size": 1024,
                "mountpoint": "/var"
              }
            ],
            "packages": [ "postgresql" ],
          }
          "image_requests": [
            {
              "architecture": "x86_64",
              "image_type": "aws",
              "upload_request": {
                "options": {
                  "share_with_accounts": [
                    "123456789012"
                  ]
                },
                "type": "aws"
              }
            }
          ]

        Args:
            image_distribution: distribution name (base operating system), e.g. "rhel-8"
            image_name: image name, e.g. "packit-test-john-foo"
            image_request: Image request definition of an image build
            image_customizations: Image customizations definition of an image build
            repo_url: yum repository URL, e.g.
                "https://download.copr.fedorainfracloud.org/" +
                "results/@cockpit/cockpit-preview/centos-stream-9-x86_64/"
        """
        image_customizations.setdefault("payload_repositories", [])
        # variable assignment is done for sake of mypy:
        #   https://stackoverflow.com/a/54788883/909579
        payload_repositories: list[dict[str, Union[str, bool]]] = image_customizations[
            "payload_repositories"
        ]
        logger.debug(
            f"image_customizations -> payload_repositories {payload_repositories}",
        )
        payload = {
            "image_name": image_name,
            "distribution": image_distribution,
            "image_requests": [image_request],
            "customizations": image_customizations,
        }
        if repo_url is not None:
            payload_repositories.append(
                {
                    "rhsm": False,
                    "baseurl": repo_url,
                    # needs to be the actual key, not link:
                    # https://issues.redhat.com/browse/HMSIB-14
                    # "gpgkey": "https://download.copr.../@cockpit/cockpit-preview/pubkey.gpg",
                    "check_gpg": False,
                },
            )
        response = self.image_builder_request("POST", "compose", payload=payload)

        response_json = response.json()
        try:
            return response_json["id"]
        except KeyError as e:
            logger.error(
                f"Failed to create image ({response.status_code}): {response_json}",
            )
            raise PackitException(f"Failed to create image: {response_json}") from e

    def get_image_status(self, build_id: str):
        """
        Get image build status.

        Args:
            build_id: Build ID of the image.

        Returns:
            Status of the build (example: success, building, pending)
        """
        # Examples of /composes/{build_id}
        # {'image_status': {'status': 'building'}}
        # {'image_status': {
        #     'status': 'success', 'upload_status': {
        #         'options': {
        #             'ami': 'ami-08ee0689a0547e7ea',
        #             'region': 'us-east-1'
        #         },
        #         'status': 'success', 'type': 'aws'
        #     }
        # }
        response_json = self.image_builder_request("GET", f"composes/{build_id}").json()
        logger.debug(f"Image build metadata: {response_json}")
        return response_json["image_status"]["status"]

    def clone(self, build_id: str, region: str, share_with_accounts: list[str]):
        """
        Clone existing image into a new AWS region.

        Args:
            build_id: Build ID of the image.
            region: AWS region
            share_with_accounts: List of str of accounts to share the new image with

        Returns:
            Metadata of the clone build
        """
        response_json = self.image_builder_request(
            "POST",
            f"composes/{build_id}/clone",
            payload={
                "region": region,
                "share_with_accounts": share_with_accounts,
            },
        ).json()
        logger.debug(f"Image clone metadata: {response_json}")
        return response_json

    def get_clone(self, build_id: str):
        """
        Get image clone status.

        Args:
            build_id: Build ID of the clone image.

        Returns:
            Metadata of the clone build
        """
        response_json = self.image_builder_request("GET", f"/clones/{build_id}").json()
        logger.debug(f"Image build metadata: {response_json}")
        return response_json
