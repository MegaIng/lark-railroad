from __future__ import annotations

import sys

from railroad import Diagram

from lark2railroad import lark_parser, Lark2Railroad, Lark2HTML

tree = lark_parser.parse(open('lark.lark').read())

out = Lark2HTML().transform(tree)

print(out, file=open('lark.html', 'w'))
