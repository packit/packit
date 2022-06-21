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
from typing import Optional

from bodhi.client.bindings import BodhiClient

logger = logging.getLogger(__name__)


class OurBodhiClient(BodhiClient):
    """compat layer for bodhi 5 and 6 clients"""

    def __init__(self, fas_username: Optional[str] = None, fas_password: str = None):
        # https://docs.python.org/3/library/inspect.html#inspect.signature
        signature = inspect.signature(BodhiClient)
        try:
            # bodhi 5
            self.is_bodhi_6 = not bool(signature.parameters["username"])
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
        except KeyError:
            # bodhi 6
            self.is_bodhi_6 = True
            super().__init__()

    def refresh_auth(self):
        """clear existing authentication data and obtain new"""
        if self.is_bodhi_6:
            self.clear_auth()
            logger.info("Bodhi OIDC authentication follows.")
            self.ensure_auth()
        else:
            self._session.cookies.clear()
            self.csrf_token = None


def get_bodhi_client(
    fas_username: Optional[str] = None, fas_password: str = None
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
    return OurBodhiClient(fas_username=fas_username, fas_password=fas_password)
