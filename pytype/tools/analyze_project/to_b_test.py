import ast
import textwrap
import sys

from pytype import config
from pytype.tools.annotate_ast import annotate_ast

source_code = """
l = [1,2,3]
s = [str(i) for i in l]
"""

def annotate(source):
    source = textwrap.dedent(source.lstrip('\n'))
    pytype_options = config.Options.create(python_version=(sys.version_info.major, sys.version_info.minor))

    module = annotate_ast.annotate_source(source, ast, pytype_options)
    return module

def get_annotations_dict(module):
    return {_get_node_key(node): node.resolved_annotation for node in ast.walk(module) if hasattr(node, 'resolved_type')}

def _get_node_key(node):
    base = (node.lineno, node.__class__.__name__)

    if isinstance(node, ast.Name):
        return base + (node.id,)
    elif isinstance(node, ast.Attribute):
        return base + (node.attr,)
    elif isinstance(node, ast.FunctionDef):
        return base + (node.name,)
    else:
        return base

with open('/Users/fuyingbo/Desktop/test_project/tox/src/tox/config/loader/str_convert.py', "r") as f:
    source_code = f.read()
    ann_module = annotate(source_code)
    anns = get_annotations_dict(ann_module)
    for k, v in sorted(anns.items()):
        print(k, v)
