from __future__ import annotations

from ast import literal_eval
from io import StringIO
from textwrap import indent
from typing import Tuple
from urllib.parse import urlencode

from lark import Lark, Transformer, Discard
from railroad import NonTerminal, Terminal, Choice, OneOrMore, ZeroOrMore, Diagram, Optional, Sequence, Group, Comment, \
    Start, DEFAULT_STYLE

lark_parser = Lark.open('lark.lark', rel_to=__file__, parser='lalr')


def _eval_escaping(s):
    w = ''
    i = iter(s)
    for n in i:
        w += n
        if n == '\\':
            try:
                n2 = next(i)
            except StopIteration:
                raise ValueError("Literal ended unexpectedly (bad escaping): `%r`" % s)
            if n2 == '\\':
                w += '\\\\'
            elif n2 not in 'uxnftr':
                w += '\\'
            w += n2
    w = w.replace('\\"', '"').replace("'", "\\'")

    to_eval = "u'''%s'''" % w
    try:
        s = literal_eval(to_eval)
    except SyntaxError as e:
        raise ValueError(s, e)

    return s


def _unquote_literal(t, v) -> Tuple[str, str]:
    flag_start = v.rfind('/"'[type == 'STRING']) + 1
    assert flag_start > 0
    flags = v[flag_start:]

    v = v[:flag_start]
    assert v[0] == v[-1] and v[0] in '"/', v
    x = v[1:-1]

    s = _eval_escaping(x)

    if type == 'STRING':
        s = s.replace('\\\\', '\\')
    return s, flags


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

    def literal_range(self, children):
        start, end = children
        return Terminal(f'{start}..{end}', self._href_generator('literal_range', (start, end)))

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
            base, mi, ma = children
            if int(mi.value) == 0:
                if int(ma.value) == 1:
                    return Optional(base)
                return ZeroOrMore(base, Comment(f'{mi.value}..{ma.value}'))
            else:
                return OneOrMore(base, Comment(f'{mi.value}..{ma.value}'))
        base, op = children
        if op.type != 'OP':
            return OneOrMore(base, Comment(f'{op.value} times'))
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
        return name, Diagram(Start('complex', name.value), expansions, type='complex', css=self._css)

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
    file_name = '&lt;string&gt;'

    def __init__(self, css=DEFAULT_STYLE, file_name=None, regex_link_creator=lambda regex, flags: None,
                 get_import=lambda path: None):
        super(Lark2HTML, self).__init__(css=None)
        self._global_css = css
        if file_name is not None:
            self.file_name = file_name
        self._regex_link_creator = regex_link_creator
        self._get_import = get_import

    def _href_generator(self, node_type, value):
        if node_type in ('RULE', 'TOKEN'):
            return f'#{value}'
        elif node_type == 'REGEXP':
            regex, flags = _unquote_literal(node_type, value)
            return self._regex_link_creator(regex, flags)
        else:
            return None

    def import_path(self, children):
        return children

    def import_(self, children):
        if len(children) == 2:
            path, alias = children
        else:
            path, = children
            alias = path[-1]
        info = self._get_import(path)
        if info is None:
            raise Discard
        file_name, href = info
        t, c = {'TOKEN': ('simple', Terminal), 'RULE': ('complex', NonTerminal)}[alias.type]
        return alias.value, Diagram(Start(t, alias.value),
                                    c(f"import {path[-1].value} from {''.join(path[:-2])}[{file_name!r}]",
                                             href=href),
                                    type=t, css=self._css)

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


def regex101(regex, flags):
    return f"https://regex101.com/?{urlencode({'regex': regex, 'flavor': 'python', 'flags': flags})}"


def pythex(regex, flags):
    return f"""https://pythex.org/?{urlencode({
        'regex': regex,
        'ignorecase': int('i' in flags),
        'multiline': int('m' in flags),
        'dotall': int('s' in flags),
        'verbose': int('x' in flags)})}"""
