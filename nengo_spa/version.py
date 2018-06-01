"""Nengo SPA version information.

We use semantic versioning (see http://semver.org/).
and conform to PEP440 (see https://www.python.org/dev/peps/pep-0440/).
'.devN' will be added to the version unless the code base represents
a release version. Release versions are git tagged with the version.
"""

name = "nengo_spa"
version_info = (0, 5, 0)  # (major, minor, patch)
dev = None

version = "{v}{dev}".format(v=".".join(str(v) for v in version_info),
                            dev="" if dev is None else ".dev{:d}".format(dev))
