import pytest
from flexmock import flexmock
from requests import Session

from packit.utils.bodhi import OurBodhiClient


@pytest.mark.skipif(
    condition=not OurBodhiClient().is_bodhi_6, reason="Bodhi 6 code only"
)
def test_login_with_kerberos():
    # cannot be imported on bodhi <= 5
    from bodhi.client.oidcclient import OIDCClient

    bodhi = OurBodhiClient(
        fas_username="probably_packit", kerberos_realm="FEDORAPROJECT.ORG"
    )
    bodhi.oidc._tokens = {"access_token": "token"}
    the_code = (
        "code=d37deb2e-5463-1234-1234-ba70c75d74f4_5EH4MhV3Lj2ld1HapvvMM_r4Vy-eFX6R"
        "&amp;state=k44Rw12G86v6605oTNv6mm7yhZRGXO"
    )
    flexmock(Session).should_receive("request").and_return(
        flexmock(
            raise_for_status=lambda: None,
            text=f'<meta charset="UTF-8">\n<title>{the_code}</title>\n   ',
        )
    )
    flexmock(OIDCClient).should_receive("auth_callback").with_args(f"?{the_code}")
    bodhi.login_with_kerberos()
