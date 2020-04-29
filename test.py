from __future__ import annotations

from lark2railroad import lark_parser, Lark2HTML, regex101

tree = lark_parser.parse(open('lark.lark').read())

out = Lark2HTML(file_name='lark.lark', regex_link_creator=regex101).transform(tree)

print(out, file=open('lark.html', 'w'))
