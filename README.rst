======
epochs
======


.. image:: https://img.shields.io/pypi/v/epochs.svg
     :target: https://pypi.python.org/pypi/epochs

.. image:: https://img.shields.io/travis/mgalloy/epochs.svg
     :target: https://travis-ci.org/mgalloy/epochs

.. image:: https://readthedocs.org/projects/epochs/badge/?version=latest
     :target: https://epochs.readthedocs.io/en/latest/?badge=latest
     :alt: Documentation Status


Python package to handle configuration files specifying values changing over time


* Free software: BSD license
* Documentation: https://epochs.readthedocs.io.


Features
--------

The main features of epochs are:

* Parse date-based configuration files and retrieve values based on datetime.
* Validate configuration files, both normal and epoch date-based ones, against a specification.

For example, for a configuration file, ``epochs.cfg``, such as::

  [2019-04-09 20:27:15]
  value   : 3
  
  [2019-04-09 22:31:01]
  value   : 5

The dates can be anything parsed by `dateutil.parser.parse`_. Then, epochs can retrieve the correct value from the config file corresponding to a given date:

.. code-block:: python

  >>> import epochs
  >>> ep = epochs.parse('epochs.cfg')
  >>> value = ep.get('value', datetime='2019-04-09 21:55:45')
  >>> print(value)
  3
  >>> value = ep.get('value', datetime='2019-04-09 23:15:40')
  >>> print(value)
  5

The "correct" value is the one specified in the earliest section of the configuration file with a date on or before the given date.

Below is an example specification for a configuration file::

  [city]
  name    : required=True, type=str
  streets : required=True, type=List[str]
  temp    : required=False, type=float, default=0.0

And an example configuration file following this specification::

  [city]
  name    : Boulder
  streets : [Broadway, Baseline, Valmont]

Then to parse the configuration file with its specification:

.. code-block:: python

  >>> import epochs
  >>> cf = epochs.parse('example.cfg', spec='spec.cfg')
  >>> name = cf.get('name', section='city')
  >>> print(name)
  Boulder
  >>> streets = cf.get('streets', section='city')
  >>> print(steets)
  ['Broadway', 'Baseline', 'Valmont']
  >>> temp = cf.get('temp', section='city')
  >>> print(temp, type(temp))
  0.0 <class 'float'>


Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

.. _`dateutil.parser.parse`: https://dateutil.readthedocs.io/en/stable/parser.html
