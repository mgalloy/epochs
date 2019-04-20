===================
Specification files
===================

Specification files provide a specification for each option in a configuration file. This specification allows:

1. The `get` method can automatically return the value as the correct type, including using a default value if an optional value was not given in the configuration file.
2. The configuration file(s) can be validated against the specification to ensure all required options are provided and no extra options are given.

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
