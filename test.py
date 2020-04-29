from __future__ import annotations

from pathlib import Path

from lark import lark

from lark2railroad import lark_parser, Lark2HTML, regex101


def build_html(path: Path, target: Path = None, /, **kwargs):
    with path.open() as f:
        tree = lark_parser.parse(f.read())
    html = Lark2HTML(file_name=path.name, **kwargs).transform(tree)
    if target is None:
        target = path.with_suffix('.html')
    with target.open('w') as f:
        f.write(html)


common_path = Path(lark.__file__).parent / 'grammars' / 'common.lark'

build_html(common_path, Path('common.html'), regex_link_creator=regex101)
build_html(Path('lark.lark'), regex_link_creator=regex101)
build_html(Path('test.lark'), regex_link_creator=regex101)
