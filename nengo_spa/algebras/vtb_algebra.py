import nengo
import numpy as np

from nengo_spa.algebras.base import AbstractAlgebra
from nengo_spa.networks.vtb import VTB


class VtbAlgebra(AbstractAlgebra):
    r"""Vector-derived Transformation Binding (VTB) algebra.

    VTB uses elementwise addition for superposition. The binding operation
    :math:`\mathcal{B}(x, y)` is defined as

    .. math::

       \mathcal{B}(x, y) := V_y x = \left[\begin{array}{ccc}
           V_y' &    0 &    0 \\
              0 & V_y' &    0 \\
              0 &    0 & V_y'
           \end{array}\right] x

    with

    .. math::

       V_y' = d^{\frac{1}{4}} \left[\begin{array}{cccc}
           y_1            & y_2            & \dots  & y_{d'}  \\
           y_{d' + 1}     & y_{d' + 2}     & \dots  & y_{2d'} \\
           \vdots         & \vdots         & \ddots & \vdots  \\
           y_{d - d' + 1} & y_{d - d' + 2} & \dots  & y_d
       \end{array}\right]

    and

    .. math:: d'^2 = d.

    The approximate inverse :math:`y^+` for :math:`y` is permuting the elements
    such that :math:`V_{y^+} = V_y`.

    Note that VTB requires the vector dimensionality to be square.

    The VTB binding operation is neither associative nor commutative.

    Publications with further information are forthcoming.
    """

    _instance = None

    def __new__(cls):
        if type(cls._instance) is not cls:
            cls._instance = super(VtbAlgebra, cls).__new__(cls)
        return cls._instance

    def is_valid_dimensionality(self, d):
        """Checks whether *d* is a valid vector dimensionality.

        For VTB all square numbers are valid dimensionalities.

        Parameters
        ----------
        d : int
            Dimensionality

        Returns
        -------
        bool
            *True*, if *d* is a valid vector dimensionality for the use with
            the algebra.
        """
        if d < 1:
            return False
        sub_d = np.sqrt(d)
        return sub_d * sub_d == d

    def _get_sub_d(self, d):
        sub_d = int(np.sqrt(d))
        if sub_d * sub_d != d:
            raise ValueError("Vector dimensionality must be a square number.")
        return sub_d

    def make_unitary(self, v):
        sub_d = self._get_sub_d(len(v))
        m = np.array(v.reshape((sub_d, sub_d)))
        for i in range(1, sub_d):
            y = -np.dot(m[:i, i:], m[i, i:])
            A = m[:i, :i]
            m[i, :i] = np.linalg.solve(A, y)
        m /= np.linalg.norm(m, axis=1)[:, None]
        m /= np.sqrt(sub_d)
        return m.flatten()

    def superpose(self, a, b):
        return a + b

    def bind(self, a, b):
        d = len(a)
        if len(b) != d:
            raise ValueError("Inputs must have same length.")
        m = self.get_binding_matrix(b)
        return np.dot(m, a)

    def invert(self, v):
        sub_d = self._get_sub_d(len(v))
        return v.reshape((sub_d, sub_d)).T.flatten()

    def get_binding_matrix(self, v, swap_inputs=False):
        sub_d = self._get_sub_d(len(v))
        m = np.sqrt(sub_d) * np.kron(np.eye(sub_d), v.reshape((sub_d, sub_d)))
        if swap_inputs:
            m = np.dot(self.get_swapping_matrix(len(v)), m)
        return m

    def get_swapping_matrix(self, d):
        """Get matrix to swap operands in bound state.

        Parameters
        ----------
        d : int
            Dimensionality of vector.

        Returns
        -------
        (d, d) ndarry
            Matrix to multiply with a vector to switch left and right operand
            in bound state.
        """
        return self.get_inversion_matrix(d)

    def get_inversion_matrix(self, d):
        sub_d = self._get_sub_d(d)
        return np.eye(d).reshape(d, sub_d, sub_d).T.reshape(d, d)

    def implement_superposition(self, n_neurons_per_d, d, n):
        node = nengo.Node(size_in=d)
        return node, n * (node,), node

    def implement_binding(self, n_neurons_per_d, d, unbind_left, unbind_right):
        net = VTB(n_neurons_per_d, d, unbind_left, unbind_right)
        return net, (net.input_left, net.input_right), net.output

    def absorbing_element(self, d):
        """VTB has no absorbing element except the zero vector."""
        raise NotImplementedError("VtbAlgebra does not have any absorbing elements.")

    def identity_element(self, d):
        sub_d = self._get_sub_d(d)
        return (np.eye(sub_d) / d ** 0.25).flatten()

    def zero_element(self, d):
        """Return the zero element of dimensionality *d*.

        The zero element produces itself when bound to a different vector.
        For VTB this is the zero vector.

        Parameters
        ----------
        d : int
            Vector dimensionality.

        Returns
        -------
        (d,) ndarray
            Zero element.
        """
        return np.zeros(d)
