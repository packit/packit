from tests.unit.zuul_funcs import hello


def test_zuul():
    assert hello() == "hello"
