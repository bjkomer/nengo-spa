try:
    from pytest_nengo import (  # pylint: disable=unused-import
        pytest_configure,
        pytest_runtest_setup,
    )
except ImportError:
    import nengo
    import pytest

    @pytest.fixture(scope="session")
    def Simulator(request):
        return nengo.Simulator


from nengo_spa.algebras.hrr_algebra import HrrAlgebra
from nengo_spa.algebras.vtb_algebra import VtbAlgebra


class TestConfig(object):
    """Parameters affecting all Nengo SPA testes.

    These are essentially global variables used by py.test to modify aspects
    of the Nengo SPA tests. We collect them in this class to provide a mini
    namespace and to avoid using the ``global`` keyword.

    The values below are defaults. The functions in the remainder of this
    module modify these values accordingly.
    """

    algebras = [HrrAlgebra(), VtbAlgebra()]


def pytest_generate_tests(metafunc):
    if "algebra" in metafunc.fixturenames:
        metafunc.parametrize("algebra", [a for a in TestConfig.algebras])
