import ast
import textwrap
import sys

from pytype import config
from pytype.tools.annotate_ast import annotate_ast

source_code = """
l: = [1, 's', 2]	# infered as List[Union[int, str]]
l1 = l[0:2]		# infered as Union[List[int], List[str]]
l2 = l[0:1]		# infered as Union[List[int], List[str]]
l3 = l[1]
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
    # source_code = f.read()
    ann_module = annotate(source_code)
    anns = get_annotations_dict(ann_module)
    for k, v in sorted(anns.items()):
        print(k, v)
