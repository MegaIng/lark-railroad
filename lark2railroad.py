from __future__ import annotations

from io import StringIO
from textwrap import indent

from lark import Lark, Transformer, Discard
from railroad import NonTerminal, Terminal, Choice, OneOrMore, ZeroOrMore, Diagram, Optional, Sequence, Group, Comment, \
    Start, DEFAULT_STYLE

lark_parser = Lark.open('lark.lark', rel_to=__file__, parser='lalr')


class Lark2Railroad(Transformer):
    def __init__(self, css=DEFAULT_STYLE):
        super(Lark2Railroad, self).__init__()
        self._css = css

    def __default__(self, data, children, meta):
        raise ValueError((data, children))

    def _href_generator(self, node_type, value):
        return None

    def rule_params(self, children):
        if len(children) != 0:
            raise ValueError("Rule templates are currently not supported")
        raise Discard

    def token_params(self, children):
        if len(children) != 0:
            raise ValueError("Token templates are currently not supported")
        raise Discard

    def name(self, children):
        name, = children
        return {'RULE': NonTerminal, 'TOKEN': Terminal}[name.type] \
            (name.value, href=self._href_generator(name.type, name.value))

    def literal(self, children):
        value, = children
        return Terminal(value.value, href=self._href_generator(value.type, value.value))

    def expansion(self, children):
        return Sequence(*children)

    def expansions(self, children):
        return Choice(0, *children)

    def maybe(self, children):
        return Optional(children[0])

    def alias(self, children):
        base, name = children
        return Group(base, name.value)

    def expr(self, children):
        if len(children) == 3:
            raise ValueError("Repetitions '(...)~a..b' are currently not supported")
        base, op = children
        if op.type != 'OP':
            raise ValueError("Repetitions '(...)~a' are currently not supported")
        if op.value == '+':
            return OneOrMore(base)
        elif op.value == '*':
            return ZeroOrMore(base)
        elif op.value == '?':
            return Optional(base)
        else:
            raise ValueError(f"Unsupported Operator {op!r}")

    def rule(self, children):
        name, expansions = children
        return name, Diagram(Start('complex', name.value), expansions, type='complex')

    def token(self, children):
        name, expansions = children
        return name, Diagram(Start('simple', name.value), expansions, type='simple', css=self._css)

    def _ignore_this_node(self, children):
        raise Discard

    import_path = import_ = ignore = _ignore_this_node

    def start(self, children):
        return children


HTML_TEMPLATE = """\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">

  <title>Grammar railroad diagram for {file_name!r}</title>

  <style type='text/css'>
  {style}
  </style>
</head>

<body>
  {diagrams}
</body>
</html>\
"""

DIAGRAM_TEMPLATE = """
  <div id='{id}'>
{svg}
  </div>
"""


class Lark2HTML(Lark2Railroad):
    file_name: str = '&lt;string&gt;'

    def __init__(self, css=DEFAULT_STYLE):
        super(Lark2HTML, self).__init__(css=None)
        self._global_css = css

    def _href_generator(self, node_type, value):
        if node_type in ('RULE', 'TOKEN'):
            return f'#{value}'
        else:
            return None

    def start(self, children):
        diagrams = []
        for name, d in children:
            d: Diagram
            buffer = StringIO()
            d.writeSvg(buffer.write)
            diagrams.append(DIAGRAM_TEMPLATE.format(id=name.lstrip('?!'), svg=indent(buffer.getvalue(), '    ')))
        diagrams = '<br>'.join(diagrams)
        return HTML_TEMPLATE.format(
            file_name=self.file_name,
            style=self._global_css,
            diagrams=diagrams
        )
