.. toctree::
   :hidden:

   Intro <self>
   api

=============================
How – yamap – YAML to Python!
=============================

Using complex YAML configuration files in Python used to be painful.
Until now you had the choice of

* reading into a datastructure of basic types (dicts, lists, scalars)
  and then traversing that, littering your code with dictonary keys,

* spreading a big helping of custom YAML tags over your files and
  adding constructors to turn these into data classes,

* or wrestling with PyYAML’s experimental path constructors.

None of these is fun and only the last one halfhartedly solves to issue
of validating the structure of your files.

yamap to the rescue. It's the bastard child of a YAML to Python data
mapper and a schema definition DSL and validator.

Basic example
=============

Given a YAML file

.. code-block:: yaml

   command: /usr/bin/echo
   arguments:
     - Hello
     - world,
     - ${NAME}
   env: { NAME: Bob }
   capture: true
   timeout: 5.5

you can easily us yamap to parse that

.. code-block:: python

   from yamap import *

   schema = (
     yamap()
       .exactly_one('command',   yastr(value='/.+'))
       .zero_or_one('arguments', yaseq().case(yastr))
       .zero_or_one('env',       yamap().zero_or_more('[A-Z]+', yastr))
       .zero_or_one('capture',   yabool)
       .zero_or_one('timeout',   yanumber)
   )

   result = schema.load(...)

which will return you this Python object tree

.. code-block:: python

   { 'command': '/usr/bin/echo',
     'arguments': ['Hello', 'world,', '${NAME}'],
     'env': {'NAME': 'Bob'},
     'capture': True }

Easy but no different to using a plain YAML parser like
`pyyaml <https://github.com/yaml/pyyaml>`_ or
`ruamel.yaml <https://sourceforge.net/projects/ruamel-yaml>`_ so let's
dive a bit deeper what else **yamap** has in store for you.

Mapping YAML types to Python
============================

To use **yamap** you'll need to define a schema tree of data types that
describe the layout of the YAML data you are expecting to parse. Loading
a file that doesn't adhere to this schema will make **yamap** throw a
:exc:`MappingError <yamap.errors.MappingError>`.

All schema types are immutable but provide methods that return modified
copies of them. This allows easy method chaining and reuse of schema
trees within or across schemas.

Schema types are matched to the YAML data by means of the YAML tags
returned by the file parser.


Scalar data types
-----------------
These are the "leafs" of a YAML schema tree and get turned into the
corresponding simple Python objects:

- :class:`yaint <yamap.schema.yaint>` matches *tag:yaml.org,2002:int* and
  constructs Python :obj:`int`.
- :class:`yafloat <yamap.schema.yafloat>` matches *tag:yaml.org,2002:float*
  and constructs Python :obj:`float`.
- :class:`yanumber <yamap.schema.yanumber>` matches any of the two
  afore types and constructs either Python :obj:`int` or :obj:`float`
  accordingly.
- :class:`yastr <yamap.schema.yastr>` matches *tag:yaml.org,2002:str*
  and constructs Python :obj:`str`.
- :class:`yabool <yamap.schema.yabool>` matches *tag:yaml.org,2002:bool*
  and constructs Python :obj:`bool`.
- :class:`yanull <yamap.schema.yanull>` matches *tag:yaml.org,2002:null*
  and constructs Python :obj:`None`.
- :class:`yascalar <yamap.schema.yascalar>` matches any of the afore
  mentioned and constructs accordingly.

In addition to matching by tag, :class:`yascalar <yamap.schema.yascalar>`
(and thus all other scalar types as these derive from it) you can pass
it a regex on construction. **yamap** will try to
:func:`fullmatch() <re.fullmatch>` this against the node value
(being the unconstructed :obj:`str` from the YAML data) and throw a
:exc:`MappingError <yamap.errors.MappingError>` if this doesn't succeed.
