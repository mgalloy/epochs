===================
Specification files
===================

Specification files provide a specification for each option in a configuration file. This specification allows:

1. the ``get`` method to automatically return the value as the correct type
2. the ``get`` method to return a default value if an optional value was not given in the configuration file
3. the configuration file(s) to be validated against the specification to ensure all required options are provided and no extra options are given.

For example, a specification file might look like the following:

.. code-block:: text

  [logging]
  basedir       : type=str
  level         : type=str, default=DEBUG
  rotate        : type=bool, default=YES
  max_version   : type=int, default=9
  max_width     : type=int, default=90

  [level1]
  wavelengths   : type=List[float], default=[]
  wavetypes     : type=List[str], default="[1074, 1079, 1083]"

The configuration file that uses this specification might be like:

.. code-block:: text

  [logging]
  basedir       : /Users/mgalloy/data
  level         : DEBUG
  rotate        : NO
  max_version   : 3

  [level1]
  wavelengths   : [1074.7, 1079.8, 1083.0]

The possible attributes for an option are listed below.

required
  whether the option is required; allowed values (case-insensitive) for required are "True", "YES", or "1" and "False", "NO", or "0" for not required 
type
  Python type: ``str`` (default), ``int``, ``float``, ``bool``/``boolean`` or ``List[]`` of one of the scalar types i.e., ``List[int]``
default
  default value if the option is not specified


Specification files for epoch configuration files use only the ``DEFAULT`` section whereas specification files for standard configuration files mirror the same sections as their configuration files.