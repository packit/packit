# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
"""
Initialise the Bodhi client.

Bodhi 6+ prints a URL which you need to open in browser and paste 'code=XXX...' into
terminal which the bodhi-client will save to `~/.config/bodhi/client.json`.
Bodhi 6 does not use username, password nor keytab.
"""
import os

from bodhi.client.bindings import BodhiClient


def get_bodhi_client() -> BodhiClient:
    """
    Provide an instance of BodhiClient

    Note for tests:
    * Don't mock the Bodhi instantiation via
      `flexmock(bodhi.client.bindings.BodhiClient).new_instances(bodhi_instance_mock)`
      what can affect other tests.
    * Mock this function instead -- for example:
      `flexmock(aliases).should_receive("get_bodhi_client").and_return(bodhi_instance_mock)`
    """
    return BodhiClient(
        oidc_storage_path=os.path.join(os.environ["HOME"], "bodhi-client.json"),
    )
