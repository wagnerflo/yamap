# How – yamap – YAML to Python!

yamap is the bastard child of a YAML to Python data mapper and a schema
definition DSL and validator. It tries to

- make loading YAML files easy
- while also giving you the option to build a tree of custom objects
- and at the same time verify that your files adhere to a structure
- defined using a simple tree of type-objects.

Given a YAML file

```yaml
command: /usr/bin/echo
arguments:
  - Hello
  - world,
  - ${NAME}
env: { NAME: Bob }
capture: true
timeout: 5.5
```
you can easily us yamap to parse that

```python
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
```
which will return you this Python object tree

```python
{ 'command': '/usr/bin/echo',
  'arguments': ['Hello', 'world,', '${NAME}'],
  'env': {'NAME': 'Bob'},
  'capture': True,
  'timeout': 5.5 }
```

For more details see the [documentation](https://yamap.readthedocs.io).
