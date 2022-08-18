# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT
from requre.cassette import DataTypes
from requre.modules_decorate_all_methods import record_requests_module

from packit.vm_image_build import ImageBuilder
from tests_recording.testbase import PackitTest


@record_requests_module
class TestLocalProject(PackitTest):
    """Test Image Builder API and Red Hat Auth requests"""

    def cassette_setup(self, cassette):
        """requre requires this method to be present"""
        cassette.data_miner.data_type = DataTypes.Dict

    def test_get_token(self):
        """Test PR checkout with and without merging"""

        ib = ImageBuilder(refresh_token=self.config.redhat_api_refresh_token)
        ib.refresh_auth()

        assert (
            ib.image_builder_session.headers["Authorization"]
            == f"Bearer {ib._access_token}"
        )

    def test_token_auto_refresh(self):
        """make sure that 401 requests obtain a new API token"""

        ib = ImageBuilder(refresh_token=self.config.redhat_api_refresh_token)
        # when regenerating this, go to https://console.redhat.com/insights/image-builder
        # and find a successful build of an image
        response_json = ib.image_builder_request(
            "GET", "composes/e31d475a-1d32-4cac-844e-a6a613f80439"
        ).json()
        assert response_json["image_status"]["status"] == "success"
