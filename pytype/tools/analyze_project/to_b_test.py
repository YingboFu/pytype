import ast
import textwrap
import sys

from pytype import config
from pytype.tools.annotate_ast import annotate_ast

source_code = """
def fib(n):
    res = []
    for i in range(n):
        if i == 0:
            res.append(0)
        elif i == 1:
            res.append(1)
        else:
            res.append(res[i-1]+res[i-2])
    return "res"


def is_in_fib(x, n):
    fib_res = fib(n)
    return x in fib_res


in_x = 99
in_n = "some random string"
if is_in_fib(in_x, in_n):
    print(f"{in_x} is a first fibonacci {in_n} number")
else:
    print(f"{in_x} is not a first fibonacci {in_n} number")
"""

source_code2 = """
import math

def doMath(num):
    return math.sqrt(num + 1.337)

def doMath2(num: float):
    return math.sqrt(num + 1.337)

def sayHello(num):
    r = doMath(num) + doMath2(num)
    print(f"Hello Number {r:2.4f}")
    return str(r)

def test(random):
    return sayHello(random)

def f():
    class A: pass
    return {A: A()}

def g(x):
    return {x: x()}

if __name__ == '__main__':
    print(f())
    print(g(int))
    test("some random text")
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

with open("/Users/fuyingbo/Desktop/dataset/offu---WeRoBot/werobot/client.py", "r") as f:
    source_code = f.read()
    ann_module = annotate(source_code)
    anns = get_annotations_dict(ann_module)
    for k, v in sorted(anns.items()):
        print(k, v)
