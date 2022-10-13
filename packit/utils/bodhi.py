# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
"""
Initialise the Bodhi client.

Bodhi 5 will prompt for username and password
if the values are not set and the session is not cached.
(The session is stored as `~/.fedora/openidbaseclient-sessions.cache`.)

When username and password is configured, we are not caching the session
to avoid any caching issues (mainly for the service).

Bodhi 6 prints a URL which you need to open in browser and paste 'code=XXX...' into
terminal which the bodhi-client will save to `~/.config/bodhi/client.json`.
Bodhi 6 does not use username, password nor keytab.
"""
import inspect
import logging
import os
import re
from typing import Optional

import requests
from bodhi.client.bindings import BodhiClient
from requests_kerberos import HTTPKerberosAuth, OPTIONAL

from packit.exceptions import PackitException

logger = logging.getLogger(__name__)


class OurBodhiClient(BodhiClient):
    """compat layer for bodhi 5 and 6 clients"""

    def __init__(
        self,
        fas_username: Optional[str] = None,
        fas_password: str = None,
        kerberos_realm: str = None,
    ):
        """
        Args:
            fas_username: username for FAS
              Bodhi 5 - used for authentication
              Bodhi 6 - used to construct Kerberos principal
            fas_password: password for FAS
            kerberos_realm: Kerberos realm (after @), used for Bodhi 6
        """
        self.kerberos_realm = kerberos_realm
        self.fas_username = fas_username
        # https://docs.python.org/3/library/inspect.html#inspect.signature
        signature = inspect.signature(BodhiClient)
        try:
            # bodhi 5
            self.is_bodhi_6 = not bool(signature.parameters["username"])
        except KeyError:
            # bodhi 6
            self.is_bodhi_6 = True
            super().__init__()
            # in our openshift deployment, ~/.config is not writable, but $HOME is
            # so let's put the token there
            # TODO: implement once bodhi 6.1 will be out:
            #       https://github.com/fedora-infra/bodhi/pull/4603
            if not os.access(self.oidc.storage.path, os.W_OK):
                self.oidc.storage.path = os.path.join(
                    os.environ["HOME"], "bodhi-client.json"
                )
        else:
            # bodhi 5
            logger.debug(
                f'Initialisation of the Bodhi client: FAS user {fas_username or "not configured"}; '
                f'password {"provided" if fas_password else "not configured"}'
            )
            super().__init__(
                username=fas_username,
                password=fas_password,
                cache_session=not bool(fas_username and fas_password),
                retries=3,
            )

    def ensure_auth(self):
        """clear existing authentication data and obtain new"""
        if self.is_bodhi_6:
            # DO NOT TRY to be smart here: let all the authentication up to bodhi
            super().ensure_auth()
        else:
            self._session.cookies.clear()
            self.csrf_token = None

    def login_with_kerberos(self):
        """Login to the OIDC provider using local TGT.

        We are planning to "donate" this method to bodhi-client :)
        It will stay here until that contribution is accepted, released and available

        How to test:
        1. obtain a TGT via `kinit` command for your FAS account
        2. `bodhi = OurBodhiClient(fas_username="YOUR_FAS", kerberos_realm="FEDORAPROJECT.ORG")`
        3. `bodhi.login_with_kerberos()`
        4. A file with tokens should exist: `~/.config/bodhi/client.json`

        Raises:
            PackitException if there is a problem during the auth process
        """
        logger.info("Obtain OIDC authentication token via Kerberos.")
        authorization_endpoint = self.oidc.metadata["authorization_endpoint"]
        uri, state_ = self.oidc.client.create_authorization_url(authorization_endpoint)
        response = requests.get(
            uri,
            auth=HTTPKerberosAuth(
                principal=f"{self.fas_username}@{self.kerberos_realm}",
                # I honestly don't know what the mutual_auth is in kerberos context
                # but required is not working with id.fedoraproject.org
                mutual_authentication=OPTIONAL,
            ),
        )
        response.raise_for_status()
        try:
            value = re.findall(
                r"<title>\s*(code=[\w\-_=;&]+)\s*</title>", response.text
            )[0]
        except IndexError:
            # should we logger.debug(response.text)?
            raise PackitException(
                f'Unable to locate OIDC code in the response from "{uri}".'
            )
        self.oidc.auth_callback(f"?{value}")
        if not self.oidc.tokens:
            raise PackitException(
                "Unable to obtain API token during OIDC authentication."
            )


def get_bodhi_client(
    fas_username: Optional[str] = None,
    fas_password: str = None,
    kerberos_realm: str = None,
) -> OurBodhiClient:
    """
    Provide an instance of OurBodhiClient

    Note for tests:
    * Don't mock the Bodhi instantiation via
      `flexmock(bodhi.client.bindings.BodhiClient).new_instances(bodhi_instance_mock)`
      what can affect other tests.
    * Mock this function instead -- for example:
      `flexmock(aliases).should_receive("get_bodhi_client").and_return(bodhi_instance_mock)`
    """
    return OurBodhiClient(
        fas_username=fas_username,
        fas_password=fas_password,
        kerberos_realm=kerberos_realm,
    )
