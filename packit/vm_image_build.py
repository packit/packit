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
from typing import Optional, Dict, List, Union

import requests

from packit.exceptions import PackitException

logger = logging.getLogger("packit")
REDHAT_SSO_AUTH_URL = (
    "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token"
)
REDHAT_API_GET_USER_URL = "https://api.access.redhat.com/account/v1/user"
IMAGE_BUILDER_API_URL = "https://console.redhat.com/api/image-builder/v1"


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

        self.image_builder_session = requests.Session()
        self.refresh_auth()

    def refresh_auth(self):
        """
        Refresh the access token and the image_builder_session headers.
        """
        self._access_token = self._get_access_token()
        # TODO: raise if access token is None
        self.image_builder_session.headers.update(
            {
                "Authorization": f"Bearer {self._access_token}",
                "Accept": "application/json",
            }
        )

    def image_builder_request(
        self, method: str, path: str, payload: Optional[dict] = None
    ):
        """
        Request to the Image Builder API.

        Args:
            method: HTTP method to use (GET, POST, PUT, DELETE)
            path: path to the API endpoint
            payload: payload to send with the request

        Returns:
            requests.Response object.
        """
        # don't try to refresh twice
        token_is_fresh = False
        while True:
            # TODO: figure out retries if something goes wrong here
            response = self.image_builder_session.request(
                method, f"{IMAGE_BUILDER_API_URL}/{path}", json=payload
            )
            if response.status_code == 401 and not token_is_fresh:
                token_is_fresh = True
                self.refresh_auth()
                continue
            response.raise_for_status()
            return response

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
                f"Failed to get access token ({response.status_code}): {response_json}"
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
        json_output = response.json()
        return json_output

    def create_image(
        self,
        image_distribution: str,
        image_name: str,
        image_request: Dict,
        image_customizations: Dict,
        repo_url: str,
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
        payload_repositories: List[Dict[str, Union[str, bool]]] = image_customizations[
            "payload_repositories"
        ]
        logger.debug(
            f"image_customizations -> payload_repositories {payload_repositories}"
        )
        payload = {
            "image_name": image_name,
            "distribution": image_distribution,
            "image_requests": [image_request],
            "customizations": image_customizations,
        }
        payload_repositories.append(
            {
                "rhsm": False,
                "baseurl": repo_url,
                # needs to be the actual key, not link:
                # https://issues.redhat.com/browse/HMSIB-14
                # "gpgkey": "https://download.copr.../@cockpit/cockpit-preview/pubkey.gpg",
                "check_gpg": False,
            }
        )
        response = self.image_builder_request("POST", "compose", payload=payload)

        response_json = response.json()
        try:
            return response_json["id"]
        except KeyError:
            logger.error(
                f"Failed to create image ({response.status_code}): {response_json}"
            )
            raise PackitException(f"Failed to create image: {response_json}")

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
