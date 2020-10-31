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

you can easily us yamap to parse that

.. code-block:: python

   from yamap import *

   schema = (
       yadict()
           .required('command', yastr)
           .optional('arguments', yalist(yastr))
           .optional(
               'env',
               yadict()
                   .zero_or_more('[A-Z]+', yastr)
           )
   )
