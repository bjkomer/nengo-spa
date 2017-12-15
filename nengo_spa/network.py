import inspect

import nengo
from nengo.config import Config, SupportDefaultsMixin
import numpy as np

from nengo_spa import ast_dynamic
from nengo_spa.ast2 import (
    input_network_registry, input_vocab_registry, output_vocab_registry, Node)
from nengo_spa.ast_dynamic import as_node, ModuleInput, ModuleOutput
from nengo_spa.exceptions import SpaTypeError
from nengo_spa.types import TScalar, TVocabulary
from nengo_spa.vocab import VocabularyMap, VocabularyMapParam


class _AutoConfig(object):
    def __init__(self, cfg):
        self._cfg = cfg

    def __getattr__(self, name):
        return getattr(self._cfg, name)

    def __getitem__(self, key):
        if inspect.isclass(key) and key not in self._cfg.params:
            self._cfg.configures(key)
        return self._cfg[key]


def as_ast_node(obj):
    obj = as_node(obj)
    if isinstance(obj, Node):
        return obj
    if isinstance(obj, Network):
        output = obj.output
    else:
        output = obj
    vocab = output_vocab_registry[output]
    if vocab is None:
        return ModuleOutput(output, TScalar)
    else:
        return ModuleOutput(output, TVocabulary(vocab))


def as_sink(obj):
    if isinstance(obj, Network):
        input_ = obj.input
    else:
        input_ = obj
    try:
        vocab = input_vocab_registry[input_]
    except (KeyError, TypeError):  # Trying to create weakref can raise TypeErr
        raise SpaTypeError("Invalid sink.")
    if vocab is None:
        return ModuleInput(input_, TScalar)
    else:
        return ModuleInput(input_, TVocabulary(vocab))


class SpaOperatorMixin(object):
    @staticmethod
    def __define_unary_op(op):
        def op_impl(self):
            return getattr(as_ast_node(self), op)()
        return op_impl

    @staticmethod
    def __define_binary_op(op):
        def op_impl(self, other):
            return getattr(as_ast_node(self), op)(as_ast_node(other))
        return op_impl

    __invert__ = __define_unary_op.__func__('__invert__')
    __neg__ = __define_unary_op.__func__('__neg__')

    __add__ = __define_binary_op.__func__('__add__')
    __radd__ = __define_binary_op.__func__('__radd__')
    __sub__ = __define_binary_op.__func__('__sub__')
    __rsub__ = __define_binary_op.__func__('__rsub__')
    __mul__ = __define_binary_op.__func__('__mul__')
    __rmul__ = __define_binary_op.__func__('__rmul__')

    def __rshift__(self, other):
        return as_ast_node(self) >> as_sink(other)

    def __rrshift__(self, other):
        return as_ast_node(other) >> as_sink(self)

    dot = __define_binary_op.__func__('dot')
    rdot = __define_binary_op.__func__('rdot')

    def reinterpret(self, vocab=None):
        return as_ast_node(self).reinterpret(vocab)

    def translate(self, vocab, populate=None, keys=None, solver=None):
        return as_ast_node(self).translate(vocab, populate, keys, solver)


def ifmax(condition, *actions):
    return ast_dynamic.ifmax(as_ast_node(condition), *actions)


class Network(nengo.Network, SupportDefaultsMixin, SpaOperatorMixin):
    """Base class for SPA networks.

    SPA networks are networks that also have a list of inputs and outputs,
    each with an associated `.Vocabulary` (or a desired dimensionality for
    the vocabulary).

    The inputs and outputs are dictionaries that map a name to an
    (object, Vocabulary) pair. The object can be a `.Node` or an `.Ensemble`.
    """

    vocabs = VocabularyMapParam('vocabs', default=None, optional=False)

    _input_types = {}
    _output_types = {}

    def __init__(
            self, label=None, seed=None, add_to_container=None, vocabs=None):
        super(Network, self).__init__(label, seed, add_to_container)
        self.config.configures(Network)

        if vocabs is None:
            vocabs = Config.default(Network, 'vocabs')
            if vocabs is None:
                if seed is not None:
                    rng = np.random.RandomState(seed)
                else:
                    rng = None
                vocabs = VocabularyMap(rng=rng)
        self.vocabs = vocabs
        self.config[Network].vocabs = vocabs

        self._stimuli = None

    @property
    def config(self):
        return _AutoConfig(self._config)

    @classmethod
    def get_input_vocab(cls, obj):
        return input_vocab_registry[obj]

    @classmethod
    def get_output_vocab(cls, obj):
        return output_vocab_registry[obj]

    def declare_input(self, obj, vocab):
        try:
            extended_type = self._input_types[obj.__class__]
        except KeyError:
            extended_type = type(
                'SpaInput<%s>' % obj.__class__.__name__,
                (obj.__class__, SpaOperatorMixin), {})
            self._input_types[obj.__class__] = extended_type
        obj.__class__ = extended_type
        input_vocab_registry[obj] = vocab
        input_network_registry[obj] = self

    def declare_output(self, obj, vocab):
        try:
            extended_type = self._output_types[obj.__class__]
        except KeyError:
            extended_type = type(
            'SpaOutput<%s>' % obj.__class__.__name__,
            (obj.__class__, SpaOperatorMixin), {})
            self._output_types[obj.__class__] = extended_type
        obj.__class__ = extended_type
        output_vocab_registry[obj] = vocab
        return obj


def create_inhibit_node(net, strength=2., **kwargs):
    """Creates a node that inhibits all ensembles in a network.

    Parameters
    ----------
    net : nengo.Network
        Network to inhibit.
    strength : float
        Strength of the inhibition.
    kwargs : dict
        Additional keyword arguments for the created connections from the node
        to the inhibited ensemble neurons.

    Returns
    -------
    nengo.Node
        Node that can be connected to to provide an inhibitory signal to the
        network.
    """
    inhibit_node = nengo.Node(size_in=1)
    for e in net.all_ensembles:
        nengo.Connection(
            inhibit_node, e.neurons,
            transform=-strength * np.ones((e.n_neurons, 1), **kwargs))
    return inhibit_node
