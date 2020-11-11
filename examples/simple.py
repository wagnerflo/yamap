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
    yamap()
        .exactly_one('command',   yastr)
        .zero_or_one('arguments', yaseq().case(yastr))
        .zero_or_one('env',       yamap().zero_or_more('[A-Z]+', yastr))
)

print(schema.load(yaml))
