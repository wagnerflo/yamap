yaml = '''
command: /usr/bin/echo
arguments:
  - Hello
  - world,
  - ${NAME}
env: { NAME: Bob }
capture: true
timeout: 5.5
'''

from yamap import *

schema = (
  yamap()
    .exactly_one('command',   yastr)
    .zero_or_one('arguments', yaseq().case(yastr))
    .zero_or_one('env',       yamap().zero_or_more('[A-Z]+', yastr))
    .zero_or_one('capture',   yabool)
    .zero_or_one('timeout',   yanumber)
)

print(schema.load(yaml))
