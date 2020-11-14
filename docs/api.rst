.. _api:

===========
Library API
===========

.. module:: yamap

Schema types
============

.. currentmodule:: yamap.schema
.. py:class:: yanode ([tag], [type])

   :param tag: Regular expression string to match YAML node tag against.
   :type tag: ~.str, optional
   :param type: Output type conversion function. Allows converting basic
                construction results into more complex types.
   :type type: Callable, optional


.. py:class:: yascalar ([tag], [type], [construct], [value])

   :param value: Regular expression string to match YAML node value
                 against.
   :type value: ~.str, optional
   :param construct: Basic YAML to Python construction function.
   :type construct: Callable, optional


Exceptions
==========

.. currentmodule:: yamap.errors
.. autoexception:: MappingError
