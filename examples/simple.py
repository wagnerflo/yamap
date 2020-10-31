yaml = '''
command: /usr/bin/echo
arguments:
  - Hello
  - world,
  - ${NAME}
env: { NAME: Bob }
'''

from yamap import *

schema = (
    yadict()
        .required('command',   yastr)
        .optional('arguments', yalist().can_contain(yastr))
        .optional('env',       yadict().zero_or_more('[A-Z]+', yastr))
)

print(schema.load(yaml))
