"""
This script is used to extract type annotations from python projects

It checks all annotatable code elements and extracts the presented type annotations
and assigns "NO ANNOTATION" to code elements without any type annotation
"""

import ast
import sys
from typing import List, Tuple, Union


"""
extract types from annotations and in line type comments on argument node
"""
def handle_annotation_node(arg: ast.arg,
                           slot: List[Tuple[str, str, str, str, int, int, str]],
                           filename: str,
                           fullname: str) -> None:
    if arg.arg == "self":
        return
    if arg.annotation:
        slot.append((filename, fullname, arg.arg, "ARG", arg.lineno, arg.col_offset, ast.unparse(arg.annotation)))
    elif arg.type_comment:
        slot.append((filename, fullname, arg.arg, "ARG", arg.lineno, arg.col_offset, arg.type_comment))
    else:
        slot.append((filename, fullname, arg.arg, "ARG", arg.lineno, arg.col_offset, "NO ANNOTATION"))


"""
align annotations extracted from separate line type comment with annotatable code elements
e.g. 
def headline1(text, width=80, fill_char="-"):
    # type: (str, int, str) -> str
align str, int, str with text, width, fill_char
"""
def align_annotation_with_slot(filename: str,
                               fullname: str,
                               annotations: List[str],
                               args: List[ast.arg],
                               slot: List[Tuple[str, str, str, str, int, int, str]]) -> List[str]:
    allocated_counter = 0
    for i in range(len(args)):
        arg = args[i]
        if arg.arg == 'self':
            continue
        if allocated_counter < len(annotations):
            slot.append((filename, fullname, arg.arg, "ARG", arg.lineno, arg.col_offset, annotations[allocated_counter]))
            allocated_counter += 1
        else:
            slot.append((filename, fullname, arg.arg, "ARG", arg.lineno, arg.col_offset, "NO ANNOTATION"))
    annotations = annotations[allocated_counter:]
    return annotations


"""
input: type_comment string e.g. (str, int, str) -> str
output: argument annotations e.g. [str, int, str]
"""
def extract_annotation_from_type_comments(type_comment: str) -> List[str]:
    res = []
    idx_l = type_comment.find('(')
    idx_r = type_comment.find(')')
    if idx_l != -1 and idx_r != -1:
        type_str = type_comment[idx_l + 1:idx_r]
        return process_type_comments_raw_string(type_str)
    return res


def process_type_comments_raw_string(type_comment: str) -> List[str]:
    res = []
    if type_comment != '...' and type_comment != '':
        current_level = 0
        current_type = ''
        for char in type_comment:
            if current_level == 0 and char == ',':
                res.append(current_type.strip())
                current_type = ''
            else:
                if char == '[':
                    current_level += 1
                elif char == ']':
                    current_level -= 1
                    if current_level == -1:
                        break
                current_type += char
        if current_type != '':
            res.append(current_type.strip())
    return res


"""
this function deal with type comments in separate line
e.g.
def headline1(text, width=80, fill_char="-"):
    # type: (str, int, str) -> str
"""
def handle_type_comments(node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
                         filename: str,
                         fullname: str,
                         annotations: List[str],
                         slot: List[Tuple[str, str, str, str, int, int, str]]) -> None:
    if len(node.args.posonlyargs) > 0:
        annotations = align_annotation_with_slot(filename, fullname, annotations, node.args.posonlyargs, slot)
    if len(node.args.args) > 0:
        annotations = align_annotation_with_slot(filename, fullname, annotations, node.args.args, slot)
    if node.args.vararg:
        annotations = align_annotation_with_slot(filename, fullname, annotations, [node.args.vararg], slot)
    if len(node.args.kwonlyargs) > 0:
        annotations = align_annotation_with_slot(filename, fullname, annotations, node.args.kwonlyargs, slot)
    if node.args.kwarg:
        align_annotation_with_slot(filename, fullname, annotations, [node.args.kwarg], slot)


"""
this function deal with type annotation and in-line type comments
type annotation e.g. def foo(a: int, b: int) -> int:
in-line type comments: e.g.
def headline2(
    text,           # type: str
    width=80,       # type: int
    fill_char='-',  # type: str
):                  # type: (...) -> str
"""
def handle_type_annotations(node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
                            slot: List[Tuple[str, str, str, str, int, int, str]],
                            filename: str,
                            fullname: str) -> None:
    for arg in node.args.args:
        handle_annotation_node(arg, slot, filename, fullname)
    for arg in node.args.posonlyargs:
        handle_annotation_node(arg, slot, filename, fullname)
    for arg in node.args.kwonlyargs:
        handle_annotation_node(arg, slot, filename, fullname)
    if node.args.vararg:
        arg = node.args.vararg
        handle_annotation_node(arg, slot, filename, fullname)
    if node.args.kwarg:
        arg = node.args.kwarg
        handle_annotation_node(arg, slot, filename, fullname)


"""
extract annotation for return for both type annotation and type comments
type annotation: e.g. foo(a: int, b: int) -> int:
type comments: e.g. # type: (...) -> str
"""
def handle_returns(node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
                   slot: List[Tuple[str, str, str, str, int, int, str]],
                   filename: str,
                   fullname: str) -> None:
    if node.returns:
        slot.append((filename, fullname, "N/A", "RET", node.returns.lineno, node.col_offset, ast.unparse(node.returns)))
    elif node.type_comment:
        i = node.type_comment.rfind("->")
        if i != -1:
            type_string = node.type_comment[i + 2:].strip()
            if type_string != '':
                slot.append((filename, fullname, "N/A", "RET", node.lineno, node.col_offset, type_string))
            else:
                slot.append((filename, fullname, "N/A", "RET", node.lineno, node.col_offset, "NO ANNOTATION"))
        else:
            slot.append((filename, fullname, "N/A", "RET", node.lineno, node.col_offset, "NO ANNOTATION"))
    else:
        slot.append((filename, fullname, "N/A", "RET", node.lineno, node.col_offset, "NO ANNOTATION"))


def extract_annotation_from_function_def(node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
                                         slot: List[Tuple[str, str, str, str, int, int, str]],
                                         filename: str,
                                         fullname: str) -> None:
    if node.type_comment:
        annotations = extract_annotation_from_type_comments(node.type_comment)
        if len(annotations) > 0:
            # handle type comments like: # type: (str, int, str) -> str
            handle_type_comments(node, filename, fullname, annotations, slot)
        else:
            # handle in-line type comments and type annotations
            handle_type_annotations(node, slot, filename, fullname)
    else:
        handle_type_annotations(node, slot, filename, fullname)

    handle_returns(node, slot, filename, fullname)


def self_name_handler(parent_name: str, target: ast.AST) -> str:
    target_name = ast.unparse(target)
    if target_name.startswith('self.'):
        fullname = f"{parent_name}.{target_name[target_name.find('.') + 1:]}"
    else:
        fullname = f"{parent_name}.{target_name}"
    return fullname


def extract_annotation_from_assign(node: ast.Assign,
                                   filename: str,
                                   parent_name: str) -> List[Tuple[str, str, str, str, int, int, str]]:
    slot: List[Tuple[str, str, str, str, int, int, str]] = []
    if (len(node.targets) == 1 and not isinstance(node.targets[0], ast.Tuple)
            and not isinstance(node.targets[0], ast.List)):
        fullname = self_name_handler(parent_name, node.targets[0])
        if node.type_comment:
            slot.append((filename, fullname, "N/A", "VAR", node.targets[0].lineno, node.targets[0].col_offset, node.type_comment))
        else:
            slot.append((filename, fullname, "N/A", "VAR", node.targets[0].lineno, node.targets[0].col_offset, "NO ANNOTATION"))
    return slot


def extract_types(filename, tree):
    slot: List[Tuple[str, str, str, str, int, int, str]] = []
    module_name = ''
    stack: List[List[Union[str, ast.AST]]] = [[module_name, child] for child in tree.body[::-1]]
    while stack:
        parent_name, node = stack.pop()
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            fullname = f"{parent_name}.{node.name}"
            extract_annotation_from_function_def(node, slot, filename, fullname)
            stack.extend([fullname, child] for child in node.body[::-1])
        elif isinstance(node, ast.ClassDef):
            fullname = f"{parent_name}.{node.name}"
            stack.extend([fullname, child] for child in node.body[::-1])
        elif isinstance(node, ast.Assign):
            res_ass = extract_annotation_from_assign(node, filename, parent_name)
            slot.extend(res_ass)
        elif isinstance(node, ast.AnnAssign):
            fullname = self_name_handler(parent_name, node.target)
            slot.append((filename, fullname, "N/A", "VAR", node.lineno, node.col_offset, ast.unparse(node.annotation)))
        elif isinstance(node, ast.For) or isinstance(node, ast.AsyncFor):
            stack.extend([parent_name, child] for child in node.body[::-1])
        elif isinstance(node, ast.With) or isinstance(node, ast.AsyncWith):
            stack.extend([parent_name, child] for child in node.body[::-1])
        elif isinstance(node, ast.If):
            stack.extend([parent_name, child] for child in node.orelse[::-1])
            stack.extend([parent_name, child] for child in node.body[::-1])
        elif isinstance(node, ast.While):
            stack.extend([parent_name, child] for child in node.orelse[::-1])
            stack.extend([parent_name, child] for child in node.body[::-1])
        elif isinstance(node, ast.Try):
            stack.extend([parent_name, child] for child in node.finalbody[::-1])
            stack.extend([parent_name, child] for child in node.orelse[::-1])
            for handler in node.handlers[::-1]:
                stack.extend([parent_name, child] for child in handler.body[::-1])
            stack.extend([parent_name, child] for child in node.body[::-1])
    return slot


def extract_annotation(filename: str) -> List[Tuple[str, str, str, str, int, int, str]]:
    with open(filename, 'r') as f:
        content: str = f.read()
    try:
        if sys.version_info[0] == 3 and sys.version_info[1] >= 8:
            tree: ast.Module = ast.parse(content, type_comments=True)
        else:
            tree: ast.Module = ast.parse(content)
    except:
        return []
    return extract_types(filename, tree)


for ann in extract_annotation('/Users/fuyingbo/Desktop/test_project/tox/src/tox/config/loader/str_convert.py'):
    if ann[2] != 'N/A':
        print(f"{ann[-3]}: {ann[-2]}, {ann[1][1:]}.{ann[2]}")
    elif ann[3] == 'RET':
        print(f"{ann[-3]}: {ann[-2]}, {ann[1][1:]}.return")
    else:
        print(f"{ann[-3]}: {ann[-2]}, {ann[1][1:]}")

# slots = [(22, 'StrConvert.to_path.value'),
#              (22, 'StrConvert.to_path.return'),
#              (26, 'StrConvert.to_path.value'),
#              (26, 'StrConvert.to_path.return'),
#              (30, 'StrConvert.to_list.value'),
#              (30, 'StrConvert.to_list.of_type'),
#              (30, 'StrConvert.to_list.return'),
#              (31, 'StrConvert.to_list.splitter'),
#              (32, 'StrConvert.to_list.splitter'),
#              (34, 'StrConvert.to_list.value'),
#              (39, 'StrConvert.to_set.value'),
#              (39, 'StrConvert.to_set.of_type'),
#              (39, 'StrConvert.to_set.return'),
#              (43, 'StrConvert.to_dict.value'),
#              (43, 'StrConvert.to_dict.of_type'),
#              (43, 'StrConvert.to_dict.return'),
#              (50, 'StrConvert.to_dict.msg'),
#              (54, 'StrConvert._win32_process_path_backslash.value'),
#              (54, 'StrConvert._win32_process_path_backslash.escape'),
#              (54, 'StrConvert._win32_process_path_backslash.special_chars'),
#              (54, 'StrConvert._win32_process_path_backslash.return'),
#              (61, 'StrConvert._win32_process_path_backslash.result'),
#              (65, 'StrConvert._win32_process_path_backslash.last_char'),
#              (68, 'StrConvert._win32_process_path_backslash.next_char'),
#              (74, 'StrConvert.to_command.value'),
#              (74, 'StrConvert.to_command.return'),
#              (80, 'StrConvert.to_command.value'),
#              (81, 'StrConvert.to_command.is_win'),
#              (83, 'StrConvert.to_command.s'),
#              (84, 'StrConvert.to_command.value'),
#              (89, 'StrConvert.to_command.splitter'),
#              (92, 'StrConvert.to_command.args'),
#              (93, 'StrConvert.to_command.pos'),
#              (98, 'StrConvert.to_command.arg'),
#              (100, 'StrConvert.to_command.pos'),
#              (104, 'StrConvert.to_command.msg'),
#              (107, 'StrConvert.to_command.args[0]'),
#              (108, 'StrConvert.to_command.args'),
#              (112, 'StrConvert.to_env_list.value'),
#              (112, 'StrConvert.to_env_list.return'),
#              (115, 'StrConvert.to_env_list.elements'),
#              (118, 'StrConvert.TRUTHFUL_VALUES'),
#              (119, 'StrConvert.FALSE_VALUES'),
#              (120, 'VALID_BOOL'),
#              (123, 'StrConvert.to_bool.value'),
#              (123, 'StrConvert.to_bool.return'),
#              (124, 'StrConvert.to_bool.norm'),
#              (130, 'StrConvert.to_bool.msg'),
#              (134, '<module>.__all__')]
#
# for slot in slots:
#     print(f"{slot[0]}, {slot[1]}")
