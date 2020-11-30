.. _api:

===========
Library API
===========

.. module:: yamap

Schema types
============

.. currentmodule:: yamap.schema
.. autoclass:: yatype

.. autoclass:: yanode()

   .. method:: __init__([tag: str], [type: Callable])

      :param tag: Regular expression string to match YAML node tag against.
      :param type: Output type conversion function. Allows converting basic
                   construction results into more complex types.

   .. automethod:: load

   .. method:: matches(node: Node) -> yatype

      Will try to match the given YAML node to a concrete yatype using
      :func:`fullmatch(self.tag, node.tag)<re.fullmatch>`.

.. autoclass:: yascalar()

   .. method:: __init__([tag: str], [type: Callable], [construct: Callable], [value: str])

      :param tag: See :class:`yanode <yamap.schema.yanode.__init__>`.
      :param type: See :class:`yanode <yamap.schema.yanode.__init__>`.
      :param value: Regular expression string to match YAML node value
                    against.
      :param construct: Basic YAML to Python construction function.

   .. method:: construct_leaf(SafeConstructor, Node) -> Any

      Turns the YAML node into a Python object by calling this objects
      **construct** member.

   .. method:: matches(node: Node) -> yatype

      Will try to match the given YAML node to a concrete yatype using
      :func:`fullmatch(self.tag, node.tag)<re.fullmatch>` and if the
      **value** member variable is set also
      :func:`fullmatch(self.value, node.value)<re.fullmatch>`.

.. autoclass:: yaint()

.. autoclass:: yafloat()

.. autoclass:: yanumber()

.. autoclass:: yastr()

.. autoclass:: yabool()

.. autoclass:: yanull()

.. autoclass:: yaseq()

   .. method:: __init__(tag: str = 'tag:yaml.org,2002:seq', type: Callable = list, unpack: bool = False)

      :param tag: See :class:`yanode <yamap.schema.yanode.__init__>`.
      :param type: See :class:`yanode <yamap.schema.yanode.__init__>`.
      :param unpack: If :obj:`True` call *type* with the nodes children
                     as unpacked positional arguments.

   .. automethod:: case(schema: yatype) -> yaseq

.. autoclass:: yamap()

   .. method:: __init__(tag: str = 'tag:yaml.org,2002:map', type: Callable = list, squash: bool = False, unpack: bool = False)

      :param tag: See :class:`yanode <yamap.schema.yanode.__init__>`.
      :param type: See :class:`yanode <yamap.schema.yanode.__init__>`.
      :param unpack: If :obj:`True` call *type* with the nodes children
                     as unpacked keyword arguments.
      :param unpack: If :obj:`True` call *type* only with the nodes
                     first child as argument.

   .. automethod:: zero_or_one(regex: str, schema: yatype, type: Callable = pair) -> yamap

   .. automethod:: exactly_one(regex: str, schema: yatype, type: Callable = pair) -> yamap

   .. automethod:: zero_or_more(regex: str, schema: yatype, type: Callable = pair) -> yamap

   .. automethod:: one_or_more(regex: str, schema: yatype, type: Callable = pair) -> yamap

   .. automethod:: case(regex: str, schema: yatype, type: Callable = pair, repeat: bool = False, required: bool = False) -> yamap

   .. automethod:: entry(entry: yaentry) -> yamap

.. autoclass:: yaentry()

   .. method:: __init__(required: bool = False, repeat: bool = False)

      :param required: If :obj:`True` this entry has to appear at least
                       once in its associated
                       :class:`~yamap.schema.yamap`.
      :param repeat: If :obj:`True` this entry can appear multiple times
                     in its associated :class:`~yamap.schema.yamap`.

   .. automethod:: case(pattern: str, schema: yatype, type: Callable = pair) -> yaentry

.. autoclass:: yaoneof()

   .. method:: __init__(*entries: yatype)

      :param entries: Possible schema types this node will match.

   .. automethod:: case(entry: yatype) -> yaoneof

Exceptions
==========

.. currentmodule:: yamap.errors

.. autoexception:: MappingError

.. autoexception:: NoMatchingType
