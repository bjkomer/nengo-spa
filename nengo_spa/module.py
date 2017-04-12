
import numpy as np

import nengo
from nengo.config import Config, SupportDefaultsMixin
from nengo_spa.exceptions import SpaModuleError
from nengo.network import Network
from nengo_spa.input import Input
from nengo_spa.vocab import VocabularyMap, VocabularyMapParam
from nengo.utils.compat import iteritems


def get_current_module():
    for net in reversed(Network.context):
        if isinstance(net, Module):
            return net
    return None


class _AutoConfig(object):
    def __init__(self, cfg):
        self._cfg = cfg

    def __getattr__(self, name):
        return getattr(self._cfg, name)

    def __getitem__(self, key):
        if key not in self._cfg.params:
            self._cfg.configures(key)
        return self._cfg[key]


class Module(nengo.Network, SupportDefaultsMixin):
    """Base class for SPA Modules.

    Modules are networks that also have a list of inputs and outputs,
    each with an associated `.Vocabulary` (or a desired dimensionality for
    the vocabulary).

    The inputs and outputs are dictionaries that map a name to an
    (object, Vocabulary) pair. The object can be a `.Node` or an `.Ensemble`.
    """

    vocabs = VocabularyMapParam('vocabs', default=None, optional=False)

    def __init__(
            self, label=None, seed=None, add_to_container=None, vocabs=None):
        super(Module, self).__init__(label, seed, add_to_container)
        self.config.configures(Module)

        if vocabs is None:
            vocabs = Config.default(Module, 'vocabs')
            if vocabs is None:
                if seed is not None:
                    rng = np.random.RandomState(seed)
                else:
                    rng = None
                vocabs = VocabularyMap(rng=rng)
        self.vocabs = vocabs
        self.config[Module].vocabs = vocabs

        self.__dict__['_parent_module'] = get_current_module()

        self._modules = {}

        self.inputs = {}
        self.outputs = {}

        self._stimuli = None

    @property
    def config(self):
        return _AutoConfig(self._config)

    # FIXME remove?
    @property
    def stimuli(self):
        if self._stimuli is None:
            self._stimuli = Input(self)
        return self._stimuli

    def __setattr__(self, key, value):
        """A setattr that handles Modules being added specially.

        This is so that we can use the variable name for the Module as
        the name that all of the SPA system will use to access that module.
        """
        if hasattr(self, key) and isinstance(getattr(self, key), Module):
            raise SpaModuleError("Cannot re-assign module-attribute %s to %s. "
                                 "SPA module-attributes can only be assigned "
                                 "once." % (key, value))

        super(Module, self).__setattr__(key, value)

        if isinstance(value, Module):
            self.__set_module(key, value)

    def __set_module(self, key, module):
        if module.label is None:
            module.label = key
        self._modules[key] = module
        for k, (obj, v) in iteritems(module.inputs):
            if isinstance(v, int):
                module.inputs[k] = (obj, self.vocabs.get_or_create(v))
        for k, (obj, v) in iteritems(module.outputs):
            if isinstance(v, int):
                module.outputs[k] = (obj, self.vocabs.get_or_create(v))

    def get_module(self, name, strip_output=False):
        """Return the module for the given name.

        Raises :class:`SpaModuleError` if the module cannot be found.

        Parameters
        ----------
        name : str
            Name of the module to retrieve.
        strip_output : bool, optional
            If ``True``, the module name is allowed to be followed by the name
            of an input or output that will be stripped (so the module with
            that input or output will be returned).

        Returns
        -------
        :class:`Module`
            Requested module.
        """
        try:
            components = name.split('.', 1)
            if len(components) > 1:
                head, tail = components
                return self._modules[head].get_module(
                    tail, strip_output=strip_output)
            else:
                if name in self._modules:
                    return self._modules[name]
                elif strip_output and (
                        name in self.inputs or name in self.outputs):
                    return self
                else:
                    raise KeyError
        except KeyError:
            raise SpaModuleError("Could not find module %r." % name)

    def get_module_input(self, name):
        """Return the object to connect into for the given name.

        The name will be either the same as a module, or of the form
        <module_name>.<input_name>.
        """
        try:
            components = name.split('.', 1)
            if len(components) > 1:
                head, tail = components
                return self._modules[head].get_module_input(tail)
            else:
                if name in self.inputs:
                    return self.inputs[name]
                elif name in self._modules:
                    return self._modules[name].get_module_input('default')
                else:
                    raise KeyError
        except KeyError:
            raise SpaModuleError("Could not find module input %r." % name)

    def get_input_vocab(self, name):
        return self.get_module_input(name)[1]

    def get_module_output(self, name):
        """Return the object to connect into for the given name.

        The name will be either the same as a module, or of the form
        <module_name>.<output_name>.
        """
        try:
            components = name.split('.', 1)
            if len(components) > 1:
                head, tail = components
                return self._modules[head].get_module_output(tail)
            else:
                if name in self.outputs:
                    return self.outputs[name]
                elif name in self._modules:
                    return self._modules[name].get_module_output('default')
                else:
                    raise KeyError
        except KeyError:
            raise SpaModuleError("Could not find module output %r." % name)

    def get_output_vocab(self, name):
        return self.get_module_output(name)[1]

    def similarity(self, data, probe, vocab=None):
        """Return the similarity between the probed data and corresponding
        vocabulary.

        Parameters
        ----------
        data: ProbeDict
            Collection of simulation data returned by sim.run() function call.
        probe: Probe
            Probe with desired data.
        """
        if vocab is None:
            vocab = self.vocabs[data[probe].shape[1]]
        return nengo_spa.similarity(data[probe], vocab)
