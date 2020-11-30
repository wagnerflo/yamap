# Copyright 2020 Florian Wagner <florian@wagner-flo.net>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

''' Exception classes for use in yamap. '''

from __future__ import annotations

class yaerror(Exception):
    ''' Base class for all yamap exceptions to derive from. '''

class SchemaError(yaerror):
    ''' Exception for denoting schema inconsistencies. '''

class MappingError(yaerror):
    ''' Exception for any kind or error that occurs while mapping YAML
        to Python objects using a yamap schema. '''

    def __init__(self, msg, node):
        super().__init__()
        self.msg = msg
        self.node = node

    def __str__(self):
        return '{}\n{}'.format(self.msg, self.node.start_mark)

class NoMatchingType(MappingError):
    ''' Specific MappingError that occurs when yamap can find no schema
        type to handle a YAML node. '''

    def __init__(self, node):
        super().__init__('Found no matching type', node)
