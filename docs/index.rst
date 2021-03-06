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
  and then littering your code with traversal logic and dictonary keys,

* spreading a big helping of custom YAML tags over your files and
  adding constructors to turn these into data classes,

* or wrestling with PyYAML’s experimental path constructors.

None of these is fun and only the last one halfhartedly solves to issue
of validating the structure of your files.

**yamap** to the rescue. It’s the bastard child of a YAML to Python data
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
     'capture': True,
     'timeout': 5.5 }

Easy but at first glance no different than using a plain YAML parser
like `pyyaml <https://github.com/yaml/pyyaml>`_ or
`ruamel.yaml <https://sourceforge.net/projects/ruamel-yaml>`_ so let’s
dive a bit deeper what else **yamap** has in store for you.

Mapping YAML types to Python
============================

To use **yamap** you’ll need to define a schema tree of data types that
describe the layout of the YAML data you are expecting to parse. Loading
a file that doesn’t adhere to this schema will make **yamap** throw a
:exc:`~yamap.errors.MappingError`.

All schema types are immutable but provide methods that return modified
copies of them. This allows easy method chaining and reuse of schema
trees within or across schemas.

Schema types are matched to the YAML data by means of the YAML tags
returned by the YAML parser.

Scalar data types
-----------------
These are the leafs of a YAML schema tree and get turned into the
corresponding simple Python objects:

- :class:`~yamap.schema.yaint` matches *tag:yaml.org,2002:int* and
  constructs Python :obj:`int`.
- :class:`~yamap.schema.yafloat` matches *tag:yaml.org,2002:float* and
  constructs Python :obj:`float`.
- :class:`~yamap.schema.yanumber` matches any of the two aforementioned
  types and constructs either Python :obj:`int` or :obj:`float`
  accordingly.
- :class:`~yamap.schema.yastr` matches *tag:yaml.org,2002:str* and
  constructs Python :obj:`str`.
- :class:`~yamap.schema.yabool` matches *tag:yaml.org,2002:bool* and
  constructs Python :obj:`bool`.
- :class:`~yamap.schema.yanull` matches *tag:yaml.org,2002:null* and
  constructs Python :obj:`None`.
- :class:`~yamap.schema.yascalar` matches any of the aforementioned
  types and constructs accordingly.

In addition to matching by tag, you can pass
:class:`yascalar <yamap.schema.yascalar.__init__>` (and thus all other
scalar types as these derive from it) a regex on construction. **yamap**
will try to :func:`~re.fullmatch` this against the node value (being the
unconstructed :obj:`str` from the YAML data) and throw a
:exc:`~yamap.errors.MappingError` if this doesn’t succeed.

Sequence type
-------------
The schema type :class:`~yamap.schema.yaseq` matches
*tag:yaml.org,2002:seq* will construct it's children and return them
as a Python :obj:`list`.

As such you'll need to specify what types are allowed as members of the
list using :func:`~yamap.schema.yaseq.case`

These are the branches of the YAML schema tree. The will be evalauted
once before and once after their children. First to construct a mapping
of children to schema types and second to actuall turn them into
Python types:

- :class:`~yamap.schema.yaseq` matches *tag:yaml.org,2002:seq* and
  constructs Python :obj:`list`.
- :class:`~yamap.schema.yamap` matches *tag:yaml.org,2002:map* and
  constructs Python :obj:`dict`.

Virtual data types
------------------
These don’t map to a YAML node directly but act as helpers to express
more complex schema hierarchies:

- :class:`yaoneof <yamap.schema.yaoneof>` provides a switch-case like
  alternation between schema types.
- :class:`yaentry <yamap.schema.yaentry>` helps in matching key-value
  pairs of a :class:`yamap <yamap.schema.yamap>`.

Type conversion
===============
All none-virtual schema types support passing a callable as the
constructor argument :class:`type <yamap.schema.yanode>`. That callable
will be passed the constructed value as its single argument. For
:class:`~yamap.schema.yaseq` types that is a list of elements and for
:class:`~yamap.schema.yamap` a list of key,value tuples. It is
unrestricted in its return type.

Unpacking
---------
Sometimes you'd rather have your **type** be called with unpacked
arguments or keyword arguments instead of a single list. That's what
happens when you set *unpack=True* when creating a
:class:`yaseq <yamap.schema.yaseq.__init__>` or
:class:`yamap <yamap.schema.yamap.__init__>` respectivly.

.. code-block:: python

   def hello(what='world', who='friend'):
       return 'Hello {what}, my {who}!'.format(what=what, who=who)

   schema = (
     yamap(type=hello, unpack=True)
       .zero_or_one('what', yastr)
       .zero_or_one('who',  yastr)
   )

   assert schema.load('{ who: "mate" }') == 'Hello world, my mate!'


Map squashing
-------------
Setting **squash=True** when creating a :class:`~yamap.schema.yamap`
will make the type converter be called with only the first key,value
pair of your mapping.

For example instead of having to write

.. code-block:: yaml

   - name: upper
   - name: replace
     args: [FRIEND, MATE]
   - name: replace
     args: [HELLO, HEY]

you can implement a schema to parse the much more readable

.. code-block:: yaml

   - upper
   - replace: [FRIEND, MATE]
   - replace: [HELLO, HEY]

like this

.. code-block:: python

   from yamap import *
   from dataclasses import dataclass

   def pipeline(items):
       input = 'Hello world, my friend!'
       for item in items:
           input = getattr(input, item.name)(*item.args)
       return input

   @dataclass
   class entry:
       name: str
       args: tuple = ()

   schema = (
     yaseq(type=pipeline)
       .case(yastr(type=entry))
       .case(yamap(type=entry, squash=True, unpack=True)
               .exactly_one('.+', yaseq().case(yascalar)))
   )
