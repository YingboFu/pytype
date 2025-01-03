import networkx as nx
import matplotlib.pyplot as plt
from pytype.abstract._classes import PyTDClass, ParameterizedClass, TupleClass
from datetime import datetime
from pytype.abstract._singletons import Unsolvable, Unknown
import re
import json
from pytype.tools.analyze_project.extract_annotation import get_all_annotation_slots, slot_exists

opcode_list = []  # recording all opcodes to draw the type inference graph

def remove_module_str(name):
    if strip_tag(name).startswith('<module>.'):
        if get_tag(name) != '':
            return f"{get_tag(name)} {strip_tag(name)[len('<module>.'):]}"
        else:
            return f"{strip_tag(name)[len('<module>.'):]}"
    else:
        return name

def edge_in(edge, ret):
    exist = False
    for e in ret:
        if (e[0] == edge[0] and e[1] == edge[1] and strip_tag(e[2]) == strip_tag(edge[2])
                and e[4] == edge[4] and e[5] == edge[5] and strip_tag(e[6]) == strip_tag(edge[6])):
            exist = True
    return exist

def clean_edges(edges):
    ret = []
    for edge in edges:
        # removing all type constructions
        if edge[0] == 1 or edge[4] == 1:
            continue
        if edge[6][0] == 'v' and edge[6][1:].isdigit():
            continue
        if strip_tag(edge[6]).endswith('__qualname__') or strip_tag(edge[6]).endswith('__doc__') or strip_tag(edge[6]).endswith('__module__'):
            continue
        if edge_in(edge, ret):
            continue
        if edge[0] == edge[4] and edge[1] == edge[5] and edge[2] == edge[6] and edge[3] == edge[7]:
            continue
        ret.append(edge)
    return ret

def find_obj_name_via_id(opcode_list, element):
    obj_name = ''
    for i in range(opcode_list.index(element) - 1, -1, -1):
        if ((opcode_list[i]['opcode'] == 'LOAD_CONST' or opcode_list[i]['opcode'] == 'LOAD_FAST'
             or opcode_list[i]['opcode'] == 'LOAD_NAME' or opcode_list[i]['opcode'] == 'LOAD_FOLDED_CONST'
             or opcode_list[i]['opcode'] == 'LOAD_GLOBAL') and opcode_list[i]['value_id'] == element['obj_id']):
            if opcode_list[i]['name'] == 'self':
                obj_name = opcode_list[i]['value_data'][0].name
            else:
                obj_name = opcode_list[i]['name']
            break
    return obj_name

def find_obj_name_via_data(opcode_list, element):
    obj_name = ''
    for i in range(opcode_list.index(element) - 1, -1, -1):
        if ((opcode_list[i]['opcode'] == 'LOAD_CONST' or opcode_list[i]['opcode'] == 'LOAD_FAST'
             or opcode_list[i]['opcode'] == 'LOAD_NAME' or opcode_list[i]['opcode'] == 'LOAD_FOLDED_CONST'
             or opcode_list[i]['opcode'] == 'LOAD_GLOBAL') and opcode_list[i]['value_data'] == element['obj_data']):
            if 'name' in opcode_list[i]:
                if opcode_list[i]['name'] == 'self':
                    obj_name = element['obj_data'][0].name
                else:
                    obj_name = opcode_list[i]['name']
            elif 'raw_const' in opcode_list[i]:
                obj_name = opcode_list[i]['raw_const']
            break
    return obj_name

def find_obj_name_via_id_SUBSCR(opcode_list, element, edges):
    obj_name = ''
    is_global = False
    for i in range(opcode_list.index(element) - 1, -1, -1):
        if opcode_list[i]['opcode'] == 'BINARY_OP' and opcode_list[i]['ret_id'] == element['obj_id']:
            for edge in edges:
                if edge[6] == opcode_list[i]['ret_id']:
                    obj_name = strip_tag(edge[2]).replace(element['fullname']+'.', '')
        elif opcode_list[i]['opcode'] == 'CALL' and f"v{opcode_list[i]['ret'].id}" == element['obj_id']:
            for edge in edges:
                if edge[6] == f"v{opcode_list[i]['ret'].id}":
                    obj_name = strip_tag(edge[2]).replace(element['fullname']+'.', '')
        elif ((opcode_list[i]['opcode'] == 'LOAD_CONST' or opcode_list[i]['opcode'] == 'LOAD_FAST'
             or opcode_list[i]['opcode'] == 'LOAD_NAME' or opcode_list[i]['opcode'] == 'LOAD_FOLDED_CONST'
             or opcode_list[i]['opcode'] == 'LOAD_GLOBAL' or opcode_list[i]['opcode'] == 'LOAD_CLOSURE')
              and opcode_list[i]['value_id'] == element['obj_id']):
            if opcode_list[i]['opcode'] == 'LOAD_GLOBAL':
                is_global = True
            if 'name' in opcode_list[i]:
                if opcode_list[i]['name'] == 'self':
                    obj_name = element['obj_data'][0].name
                else:
                    obj_name = opcode_list[i]['name']
            elif 'raw_const' in opcode_list[i]:
                obj_name = opcode_list[i]['raw_const']
            break
        elif ((opcode_list[i]['opcode'] == 'LOAD_ATTR' or opcode_list[i]['opcode'] == 'LOAD_METHOD')
              and opcode_list[i]['value_id'] == element['obj_id']):
            for edge in edges:
                if edge[6] == opcode_list[i]['value_id']:
                    obj_name = strip_tag(edge[2]).replace(element['fullname']+'.', '')
    return obj_name, is_global

def find_func_name(opcode_list, element):
    for i in range(opcode_list.index(element) - 1, -1, -1):
        if opcode_list[i]['opcode'] == 'MAKE_FUNCTION' and opcode_list[i]['func_var'].id == element['funcv'].id:
            return opcode_list[i]['func_name']

def find_last_yield_value_id(opcode_list, element):
    for i in range(opcode_list.index(element) - 1, -1, -1):
        if opcode_list[i]['opcode'] == 'YIELD_VALUE':
            return opcode_list[i]['send_id']

def find_map_id(opcode_list, element):
    for i in range(opcode_list.index(element) - 1, -1, -1):
        if opcode_list[i]['opcode'] == 'MAP_ADD':
            return opcode_list[i]['map_id']

def find_LIST_APPEND_item(opcode_list, list_id):
    for opcode in opcode_list:
        if opcode['opcode'] == 'LIST_APPEND' and opcode['list_id'] == list_id:
            return opcode['item_id']

def call_opcode_handler(edges, element, opcode_list):
    last_opcode = opcode_list[opcode_list.index(element)-1]
    func_name = find_func_name(opcode_list, element)
    if func_name is not None and (func_name.endswith('<listcomp>') or func_name.endswith('<genexpr>')):
        # handling listcomp and genexpr
        last_yield_value_id = find_last_yield_value_id(opcode_list, element)
        if last_yield_value_id is not None:
            edges.append([element['line'], element['offset'], f"<ITER> {last_yield_value_id}", element['ret'].data,
                          element['line'], element['offset'], f"v{element['ret'].id}", element['ret'].data])
        else:
            # handling LIST_APPEND used by the compiler e.g. for [x for x in ...]
            if last_opcode['opcode'] == 'RETURN_VALUE' and last_opcode['value_data'] == element['ret'].data:
                item_id = find_LIST_APPEND_item(opcode_list, last_opcode['value_id'])
                if item_id is not None:
                    for edge in edges:
                        if edge[6] == item_id:
                            edge[4] = element['line']
                            edge[5] = element['offset']
                            edge[6] = f"v{element['ret'].id}"
                            edge[7] = element['ret'].data
    elif func_name is not None and func_name.endswith('<dictcomp>'):
        # handling dictcomp
        map_id = find_map_id(opcode_list, element)
        for edge in edges:
            if edge[6] == map_id:
                edge[4] = element['line']
                edge[5] = element['offset']
                edge[6] = f"<DICT> v{element['ret'].id}"
                edge[7] = element['ret'].data
        edges.append([element['line'], element['offset'], f"<DICT> v{element['ret'].id}", element['ret'].data,
                      element['line'], element['offset'], f"v{element['ret'].id}", element['ret'].data])
    elif last_opcode['opcode'] == 'RETURN_VALUE' and last_opcode['value_data'] == element['ret'].data:
        # handling user-defined function calls
        for edge in edges:
            if edge[6] == last_opcode['value_id']:
                edge[4] = last_opcode['line']
                edge[5] = last_opcode['offset']
                edge[6] = remove_module_str(f"<RET> {last_opcode['fullname']}.return")
                edge[7] = last_opcode['value_data']
                edges.append([last_opcode['line'], last_opcode['offset'], remove_module_str(f"<RET> {last_opcode['fullname']}.return"), last_opcode['value_data'],
                              element['line'], element['offset'], f"v{element['ret'].id}", element['ret'].data])
    elif last_opcode['opcode'] == 'FOR_ITER' and last_opcode['func_id'] == f"v{element['funcv'].id}":
        # handling FOR_ITER
        for edge in edges:
            if edge[6] == f"v{element['funcv'].id}":
                edge[4] = element['line']
                edge[5] = element['offset']
                edge[6] = f"v{element['ret'].id}"
                edge[7] = element['ret'].data
    else:
        # handling external function calls
        call_str = ''
        func_arg_ids = []
        func_found = False
        for edge in edges:
            if edge[6] == f"v{element['funcv'].id}":
                func_found = True
                if edge[2].split('.')[-1] == 'replace':
                    for e in edges[::-1]:
                        if e[6] == edge[2]:
                            e[4] = element['line']
                            e[6] = f"v{element['ret'].id}"
                            return
                if last_opcode['opcode'] != 'FOR_ITER' or last_opcode['func_id'] != f"v{element['funcv'].id}":
                    edge[2] = f"<FUNC> {strip_tag(edge[2])}"
                    edge[3] = element['funcv'].data
                call_str += f"{strip_tag(edge[2])}("
                func_arg_ids.append(f"v{element['funcv'].id}")
        if element['posargs']:
            for arg in element['posargs']:
                for edge in edges:
                    if edge[6] == f"v{arg.id}":
                        if not edge[2].startswith('<FUNC>'):
                            edge[2] = f"<ARG> {strip_tag(edge[2])}"
                            edge[3] = arg.data
                        call_str += f"{strip_tag(edge[2]).replace(element['fullname']+'.', '')}, "
                        func_arg_ids.append(f"v{arg.id}")
        if element['namedargs']:
            for k, v in element['namedargs'].items():
                for edge in edges:
                    if edge[6] == f"v{v.id}":
                        if not edge[2].startswith('FUNC'):
                            edge[2] = f"<ARG> {strip_tag(edge[2])}"
                            edge[3] = v.data
                        call_str += f"{k}={strip_tag(edge[2]).replace(element['fullname']+'.', '')}, "
                        func_arg_ids.append(f"v{v.id}")
        if element['starargs']:
            for edge in edges:
                if edge[6] == f"v{element['starargs'].id}":
                    if not edge[2].startswith('FUNC'):
                        edge[2] = f"<ARG> {strip_tag(edge[2])}"
                        edge[3] = element['starargs'].data
                    call_str += f"*{strip_tag(edge[2]).replace(element['fullname']+'.', '')}, "
                    func_arg_ids.append(f"v{element['starargs'].id}")
        if element['starstarargs']:
            for edge in edges:
                if edge[6] == f"v{element['starstarargs'].id}":
                    if not edge[2].startswith('FUNC'):
                        edge[2] = f"<ARG> {strip_tag(edge[2])}"
                        edge[3] = element['starstarargs'].data
                    call_str += f"**{strip_tag(edge[2]).replace(element['fullname']+'.', '')}, "
                    func_arg_ids.append(f"v{element['starstarargs'].id}")
        if func_found:
            if call_str != '':
                if call_str.endswith('('):
                    call_str += ')'
                else:
                    call_str = call_str[:-2] + ')'
                if element['fullname'] != '<module>' and not call_str.startswith(element['fullname']):
                    call_str = f"{element['fullname']}.{call_str}"
                for edge in edges:
                    if edge[6] in func_arg_ids:
                        edge[4] = element['line']
                        edge[5] = element['offset']
                        edge[6] = f"<IDENT> {call_str}"
                        edge[7] = element['ret'].data
                edges.append([element['line'], element['offset'], f"<IDENT> {call_str}", element['ret'].data,
                              element['line'], element['offset'], f"v{element['ret'].id}", element['ret'].data])
        else:
            for edge in edges:
                if edge[6] in func_arg_ids:
                    edge[4] = element['line']
                    edge[5] = element['offset']
                    edge[6] = f"v{element['ret'].id}"
                    edge[7] = element['ret'].data

def _store_fast(opcode_list, element, edges, opcode):
    for i in range(opcode_list.index(element) - 1, -1, -1):
        if ((opcode_list[i]['opcode'] == 'LOAD_CONST' or opcode_list[i]['opcode'] == 'LOAD_FAST'
             or opcode_list[i]['opcode'] == 'LOAD_NAME' or opcode_list[i]['opcode'] == 'LOAD_FOLDED_CONST'
             or opcode_list[i]['opcode'] == 'LOAD_GLOBAL') and opcode_list[i]['value_data'] == element['value_data']):
            for edge in edges:
                if edge[6] == opcode_list[i]['value_id']:
                    edge[4] = element['line']
                    edge[5] = element['offset']
                    if element['name'] == 'self':
                        if opcode == 'STORE_GLOBAL':
                            edge[6] = f"<IDENT> {element['value_data'][0].name}"
                        else:
                            edge[6] = remove_module_str(f"<IDENT> {element['fullname']}.{element['value_data'][0].name}")
                    else:
                        if opcode == 'STORE_GLOBAL':
                            edge[6] = f"<IDENT> {element['name']}"
                        else:
                            edge[6] = remove_module_str(f"<IDENT> {element['fullname']}.{element['name']}")
                    edge[7] = element['value_data']
            break

def _pre_process_opcodes(opcode_list):
    # removing redundancy caused by double handling of variable annotations
    clean_opcodes = []
    redundancy = False
    ann_dict_id = 'v0'
    for op in opcode_list:
        if op['opcode'] == 'LOAD_NAME' and op['name'] == '__annotations__':
            ann_dict_id = op['value_id']
            redundancy = True
        elif op['opcode'] == 'STORE_SUBSCR' and op['obj_id'] == ann_dict_id:
            redundancy = False
            continue
        if not redundancy:
            clean_opcodes.append(op)
    return clean_opcodes

def strip_tag(name_str):
    res = []
    for s in name_str.split(' '):
        if not (s.startswith('<') and s.endswith('>')):
            res.append(s)
    return ' '.join(res)

def get_tag(name_str):
    for s in name_str.split(' '):
        if s.startswith('<') and s.endswith('>'):
            return s
    return ''

def draw_type_inference_graph(opcode_list):
    opcode_list = _pre_process_opcodes(opcode_list)
    edges = []
    for element in opcode_list:
        if element['opcode'] == 'LOAD_CONST':
            edges.append([element['line'], element['offset'], f"<CONST> {element['raw_const']}", element['value_data'],
                          element['line'], element['offset'], element['value_id'], element['value_data']])
        elif element['opcode'] == 'LOAD_NAME' or element['opcode'] == 'LOAD_CLOSURE':
            for edge in edges[::-1]:
                if strip_tag(edge[6]) == remove_module_str(f"{element['fullname']}.{element['name']}") and strip_tag(edge[2]) != strip_tag(edge[6]):
                    edges.append([edge[4], edge[5], edge[6], edge[7],
                                  element['line'], element['offset'], remove_module_str(f"<IDENT> {element['fullname']}.{element['name']}"), element['value_data']])
                    break
            edges.append([element['line'], element['offset'], remove_module_str(f"<IDENT> {element['fullname']}.{element['name']}"), element['value_data'],
                          element['line'], element['offset'], element['value_id'], element['value_data']])
        elif element['opcode'] == 'LOAD_GLOBAL':
            for edge in edges[::-1]:
                if strip_tag(edge[6]) == element['name'] and strip_tag(edge[2]) != strip_tag(edge[6]):
                    edges.append([edge[4], edge[5], edge[6], edge[7],
                                  element['line'], element['offset'], f"<IDENT> {element['name']}", element['value_data']])
                    break
            edges.append([element['line'], element['offset'], f"<IDENT> {element['name']}", element['value_data'],
                          element['line'], element['offset'], element['value_id'], element['value_data']])
        elif element['opcode'] == 'LOAD_FAST':
            if re.fullmatch(r"\.\d+", element['name']):
                # Variables with a ".n" naming scheme are things like iterators for list comprehensions
                for i in range(opcode_list.index(element) - 1, -1, -1):
                    if opcode_list[i]['opcode'] == 'GET_ITER':
                        for edge in edges:
                            if edge[6] == opcode_list[i]['itr_id']:
                                edge[4] = element['line']
                                edge[5] = element['offset']
                                edge[6] = element['value_id']
                                edge[7] = element['value_data']
                        break
            else:
                for edge in edges[::-1]:
                    if strip_tag(edge[6]) == remove_module_str(f"{element['fullname']}.{element['name']}") and strip_tag(edge[2]) != strip_tag(edge[6]):
                        if element['name'] == 'self':
                            edges.append([edge[4], edge[5], edge[6], edge[7],
                                          element['line'], element['offset'], remove_module_str(f"<IDENT> {element['fullname']}.{element['value_data'][0].name}"), element['value_data']])
                            edges.append([element['line'], element['offset'], remove_module_str(f"<IDENT> {element['fullname']}.{element['value_data'][0].name}"), element['value_data'],
                                          element['line'], element['offset'], element['value_id'], element['value_data']])
                        else:
                            edges.append([edge[4], edge[5], edge[6], edge[7],
                                          element['line'], element['offset'], remove_module_str(f"<IDENT> {element['fullname']}.{element['name']}"), element['value_data']])
                            edges.append([element['line'], element['offset'], remove_module_str(f"<IDENT> {element['fullname']}.{element['name']}"), element['value_data'],
                                          element['line'], element['offset'], element['value_id'], element['value_data']])
                        break
        elif element['opcode'] == 'LOAD_FOLDED_CONST':
            edges.append([element['line'], element['offset'], f"<CONST> {element['raw_const']}", element['value_data'],
                          element['line'], element['offset'], element['value_id'], element['value_data']])
        elif element['opcode'] == 'BINARY_OP':
            if element['name'] == '__sub__':
                pass
            if element['name'] == '__getitem__':
                x_name = ''
                y_name = ''
                for edge in edges:
                    if edge[6] == element['x_id']:
                        if x_name == '':
                            if edge[2].startswith('<FUNC>'):
                                x_name = f"{strip_tag(edge[2]).replace(element['fullname']+'.', '')}()"
                            else:
                                x_name = strip_tag(edge[2]).replace(element['fullname']+'.', '')
                        else:
                            if edge[2].startswith('<ARG>'):
                                ridx = x_name.rfind(')')
                                if ridx != -1:
                                    if x_name[ridx - 1] == '(':
                                        x_name = x_name[:ridx] + f"{strip_tag(edge[2]).replace(element['fullname']+'.', '')}" + x_name[ridx:]
                                    else:
                                        x_name = x_name[:ridx] + f", {strip_tag(edge[2]).replace(element['fullname']+'.', '')}" + x_name[ridx:]
                    if edge[6] == element['y_id']:
                        y_name = strip_tag(edge[2]).replace(element['fullname']+'.', '')
                if y_name != '':
                    for edge in edges:
                        if edge[6] == element['x_id'] or edge[6] == element['y_id']:
                            edge[4] = element['line']
                            edge[5] = element['offset']
                            edge[6] = remove_module_str(f"<IDENT> {element['fullname']}.{x_name}[{y_name}]")
                            edge[7] = element['ret_data']
                    edges.append([element['line'], element['offset'], remove_module_str(f"<IDENT> {element['fullname']}.{x_name}[{y_name}]"), element['ret_data'],
                                  element['line'], element['offset'], element['ret_id'], element['ret_data']])
                else:
                    for edge in edges:
                        if edge[6] == element['x_id'] or edge[6] == element['y_id']:
                            edge[4] = element['line']
                            edge[5] = element['offset']
                            edge[6] = element['ret_id']
                            edge[7] = element['ret_data']
            else:
                for edge in edges:
                    if edge[6] == element['x_id'] or edge[6] == element['y_id']:
                        edge[4] = element['line']
                        edge[5] = element['offset']
                        edge[6] = element['ret_id']
                        edge[7] = element['ret_data']
        elif element['opcode'] == 'STORE_GLOBAL':
            if 'annotation' in element:
                if strip_tag(edges[-1][6]).endswith('return'):
                    edges[-1][4] = element['line']
                    edges[-1][5] = element['offset']
                    edges[-1][6] = 'v0'
                edges.append([element['line'], element['offset'], f"<TYPE> {element['annotation']}", [element['annotation']],
                              element['line'], element['offset'], f"<IDENT> {element['name']}", [element['annotation']]])
            else:
                found = False
                for edge in edges:
                    if edge[6] == element['value_id']:
                        edge[4] = element['line']
                        edge[5] = element['offset']
                        edge[6] = f"<IDENT> {element['name']}"
                        edge[7] = element['value_data']
                        found = True
                if not found:
                    _store_fast(opcode_list, element, edges, 'STORE_GLOBAL')
        elif element['opcode'] == 'STORE_NAME':
            if 'annotation' in element:
                if strip_tag(edges[-1][6]).endswith('return'):
                    edges[-1][4] = element['line']
                    edges[-1][5] = element['offset']
                    edges[-1][6] = 'v0'
                edges.append([element['line'], element['offset'], f"<TYPE> {element['annotation']}", [element['annotation']],
                              element['line'], element['offset'], remove_module_str(f"<IDENT> {element['fullname']}.{element['name']}"), [element['annotation']]])
            else:
                found = False
                for edge in edges:
                    if edge[6] == element['value_id']:
                        edge[4] = element['line']
                        edge[5] = element['offset']
                        edge[6] = remove_module_str(f"<IDENT> {element['fullname']}.{element['name']}")
                        edge[7] = element['value_data']
                        found = True
                if not found:
                    _store_fast(opcode_list, element, edges, 'STORE_NAME')
        elif element['opcode'] == 'STORE_SUBSCR':
            obj_name = find_obj_name_via_id(opcode_list, element)
            for edge in edges:
                if edge[6] == element['key_id'] or edge[6] == element['value_id']:
                    edge[4] = element['line']
                    edge[5] = element['offset']
                    if obj_name != '':
                        edge[6] = remove_module_str(f"<IDENT> {element['fullname']}.{obj_name}")
                    else:
                        edge[6] = element['obj_id']
                    edge[7] = element['obj_data']
        elif element['opcode'] == 'STORE_ATTR':
            obj_name = find_obj_name_via_id(opcode_list, element)
            for edge in edges:
                if edge[6] == element['val_id']:
                    edge[4] = element['line']
                    edge[5] = element['offset']
                    edge[6] = remove_module_str(f"<IDENT> {element['fullname']}.{obj_name}.{element['name']}")
                    edge[7] = element['val_data']
        elif element['opcode'] == 'LOAD_ATTR' or element['opcode'] == 'LOAD_METHOD':
            obj_name, is_global = find_obj_name_via_id_SUBSCR(opcode_list, element, edges)
            if obj_name == '':
                obj_name = find_obj_name_via_data(opcode_list, element)
            if element['name'] == 'append':
                if is_global:
                    edges.append([element['line'], element['offset'], f"<IDENT> {obj_name}", element['obj_data'],
                                  element['line'], element['offset'], element['value_id'], element['value_data']])
                else:
                    edges.append([element['line'], element['offset'], remove_module_str(f"<IDENT> {element['fullname']}.{obj_name}"), element['obj_data'],
                                  element['line'], element['offset'], element['value_id'], element['value_data']])
            else:
                found = False
                for edge in edges:
                    if edge[6] == element['obj_id']:
                        edge[4] = element['line']
                        edge[5] = element['offset']
                        edge[6] = remove_module_str(f"<IDENT> {element['fullname']}.{obj_name}.{element['name']}")
                        edge[7] = element['value_data']
                        found = True
                if not found:
                    edges.append([element['line'], element['offset'], remove_module_str(f"<IDENT> {element['fullname']}.{obj_name}"), element['obj_data'],
                                  element['line'], element['offset'], remove_module_str(f"<IDENT> {element['fullname']}.{obj_name}.{element['name']}"), element['value_data']])
                edges.append([element['line'], element['offset'], remove_module_str(f"<IDENT> {element['fullname']}.{obj_name}.{element['name']}"), element['value_data'],
                              element['line'], element['offset'], element['value_id'], element['value_data']])
        elif element['opcode'] == 'CALL':
            call_opcode_handler(edges, element, opcode_list)
        elif element['opcode'] == 'APPEND':
            l = []
            new_item = []
            for edge in edges:
                if edge[6] == f"v{element['funcv'].id}":
                    l = edge[0:4]
                if edge[6] == f"v{element['posargs'][0].id}":
                    new_item = edge[0:4]
            if len(l) > 0 and len(new_item) > 0:
                edges.append(new_item + l)
        elif element['opcode'] == 'DICT_MERGE' or element['opcode'] == 'LIST_EXTEND':
            for edge in edges:
                if edge[6] == element['update_id']:
                    edge[4] = element['line']
                    edge[5] = element['offset']
                    edge[6] = element['target_id']
                    edge[7] = element['target_data']
        elif element['opcode'] == 'GET_ITER':
            for edge in edges:
                if edge[6] == element['seq_id']:
                    edge[4] = element['line']
                    edge[5] = element['offset']
                    edge[6] = element['itr_id']
                    edge[7] = element['itr_data']
        elif element['opcode'] == 'FOR_ITER':
            for edge in edges:
                if edge[6] == element['iter_id']:
                    edge[4] = element['line']
                    edge[5] = element['offset']
                    edge[6] = element['func_id']
                    edge[7] = element['func_data']
        elif element['opcode'] == 'UNPACK_SEQUENCE':
            for edge in edges:
                if edge[6] == element['seq_id']:
                    edge[4] = element['line']
                    edge[5] = element['offset']
                    edge[6] = f"<ITER> {element['seq_id']}"
                    edge[7] = element['seq_data']
            for value in element['values']:
                edges.append([element['line'], element['offset'], f"<ITER> {element['seq_id']}", element['seq_data'],
                              element['line'], element['offset'], f"v{value.id}", value.data])
        elif element['opcode'] == 'MAKE_FUNCTION':
            for k, ann in element['annot'].items():
                lidx = repr(ann).find("'")
                ridx = repr(ann).rfind("'")
                ann_str = repr(ann)[lidx + 1: ridx]
                if k != 'return':
                    edges.append([element['line'], element['offset'], f"<TYPE> {ann_str}", [ann_str],
                                  element['line'], element['offset'], f"<PARAM> {element['func_name']}.{k}", [ann_str]])
                else:
                    edges.append([element['line'], element['offset'], f"<TYPE> {ann_str}", [ann_str],
                                  element['line'], element['offset'], f"<RET> {element['func_name']}.{k}", [ann_str]])
            for param, _, _ in element['params']:
                if not re.fullmatch(r"\.\d+", param) and param not in element['annot']:
                    edges.append([element['line'], element['offset'], f"<TYPE> Noanno", [''],
                                  element['line'], element['offset'], f"<PARAM> {element['func_name']}.{param}", ['']])
        elif element['opcode'] == 'RETURN_VALUE':
            if ((element['frame_node_name'].startswith('Function:') and element['frame_node_name'][9:] == element['fullname']) or
                    (element['frame_node_name'].startswith('Method:') and element['frame_node_name'][7:] == element['fullname'])):
                for edge in edges:
                    if edge[6] == element['value_id']:
                        edge[4] = element['line']
                        edge[5] = element['offset']
                        edge[6] = remove_module_str(f"<RET> {element['fullname']}.return")
                        edge[7] = element['value_data']
        elif element['opcode'] == 'COMPARE_OP':
            for edge in edges:
                if edge[6] == element['x_id'] or edge[6] == element['y_id']:
                    edge[4] = element['line']
                    edge[5] = element['offset']
                    edge[6] = element['ret_id']
                    edge[7] = element['ret_data']
        elif element['opcode'] == 'BUILD_STRING':
            edges.append([element['line'], element['offset'], '<TYPE> str', ['str'],
                          element['line'], element['offset'], element['val_id'], ['str']])
        elif element['opcode'] == 'BUILD_TUPLE':
            tuple_str = ''
            elt_ids = [f"v{item.id}" for item in element['elts']]
            for edge in edges:
                if edge[6] in elt_ids:
                    if tuple_str == '':
                        if edge[2].startswith('<FUNC>'):
                            tuple_str = f"{strip_tag(edge[2]).replace(element['fullname']+'.', '')}()"
                        else:
                            tuple_str = strip_tag(edge[2]).replace(element['fullname']+'.', '')
                    else:
                        if edge[2].startswith('<FUNC>'):
                            tuple_str = tuple_str + ", " + f"{strip_tag(edge[2]).replace(element['fullname']+'.', '')}()"
                        elif edge[2].startswith('<ARG>'):
                            ridx = tuple_str.rfind(')')
                            if ridx != -1:
                                if tuple_str[ridx - 1] == '(':
                                    tuple_str = tuple_str[:ridx] + f"{strip_tag(edge[2]).replace(element['fullname']+'.', '')}" + tuple_str[ridx:]
                                else:
                                    tuple_str = tuple_str[:ridx] + f", {strip_tag(edge[2]).replace(element['fullname']+'.', '')}" + tuple_str[ridx:]
                        else:
                            tuple_str = tuple_str + ", " + strip_tag(edge[2]).replace(element['fullname']+'.', '')
            for edge in edges:
                if edge[6] in elt_ids:
                    edge[4] = element['line']
                    edge[5] = element['offset']
                    edge[6] = remove_module_str(f"<TUPLE> {element['fullname']}.{tuple_str}")
                    edge[7] = element['value_data']
            edges.append([element['line'], element['offset'], remove_module_str(f"<TUPLE> {element['fullname']}.{tuple_str}"), element['value_data'],
                          element['line'], element['offset'], element['value_id'], element['value_data']])
        elif element['opcode'] == 'YIELD_VALUE':
            for edge in edges:
                if edge[6] == element['yield_id']:
                    edge[4] = element['line']
                    edge[5] = element['offset']
                    edge[6] = f"<ITER> {element['send_id']}"
                    edge[7] = element['send_data']
        elif element['opcode'] == 'MAP_ADD':
            for edge in edges:
                if edge[6] == element['key_id'] or edge[6] == element['value_id']:
                    edge[4] = element['line']
                    edge[5] = element['offset']
                    edge[6] = element['map_id']
                    edge[7] = element['map_data']
        elif element['opcode'] == 'CALL_UD_FUNC':
            for old, new in element['old_new_var_map']:
                for k,v in element['callargs'].items():
                    if f"v{v.id}" == new:
                        to_be_removed = []
                        for edge in edges:
                            if strip_tag(edge[6]) == old and not re.fullmatch(r"\.\d+", k):
                                for e in edges:
                                    if e[6] == remove_module_str(f"<PARAM> {element['fullname']}.{k}") and e[2] == "<TYPE> Noanno":
                                        edge[4], edge[5], edge[6] = e[4], e[5], e[6]
                                        to_be_removed = e
                                        break
                        # remove the 'noanno' --> para placeholder
                        if to_be_removed:
                            edges.remove(to_be_removed)
    edges_clean = clean_edges(edges)
    return edges_clean

def has_type(data):
    return not isinstance(data[0], Unknown) and not isinstance(data[0], Unsolvable)

def solving_funcs(result, unsolved_funcs, impacted_terms):
    for k, v in unsolved_funcs.items():
        if k[2] == result:
            newly_reached = False
            fully_typed = True
            for line, offset, name, type in v:
                if slot_exists(name, impacted_terms):
                    newly_reached = True
                elif not has_type(type):
                    fully_typed = False
            if fully_typed and newly_reached and not slot_exists(result, impacted_terms):
                impacted_terms.append(k)
            break


def serialize(edges):
    res = []
    for edge in edges:
        res.append({
                        "from": {
                            "line": edge[0],
                            "offset": edge[1],
                            "name": edge[2],
                            "type": [t.__repr__() for t in edge[3]]
                        },
                        "to": {
                            "line": edge[4],
                            "offset": edge[5],
                            "name": edge[6],
                            "type": [t.__repr__() for t in edge[7]]
                        }
                    })
    return res


def calc_ann_impact(opcode_list):
    # ann_impact_res = []
    edges = draw_type_inference_graph(opcode_list)
    filename = ''
    for opcode in opcode_list:
        if 'filename' in opcode:
            filename = opcode['filename']
            break
    if filename != '':
        try:
            with open(filename.replace('.py', f"_T{datetime.now().strftime('%Y%m%d_%H%M%S')}_graph.json"), 'w') as f:
                json.dump(serialize(edges), f, indent=4)
            print("Data successfully written to 'data.json'")
        except TypeError as e:
            print("Error: Data contains non-serializable types.")
            print(f"Details: {e}")
        except Exception as e:
            print("An unexpected error occurred.")
            print(f"Details: {e}")
        # slots = get_all_annotation_slots(filename)
        # for line, offset, slot in slots:
        #     impacted_terms = [(line, offset, slot)]
        #     unsolved_funcs = {}
        #     for edge in edges:
        #         if slot_exists(strip_tag(edge[2]), unsolved_funcs.keys()):
        #             solving_funcs(strip_tag(edge[2]), unsolved_funcs, impacted_terms)
        #         if get_tag(edge[2]) in ['<IDENT>', '<ITER>', '<TUPLE>']:
        #             if slot_exists(strip_tag(edge[2]), impacted_terms) and not slot_exists(strip_tag(edge[6]), impacted_terms):
        #                 impacted_terms.append((edge[4], edge[5], strip_tag(edge[6])))
        #         elif get_tag(edge[2]) in ['<FUNC>', '<ARG>']:
        #             if not slot_exists(strip_tag(edge[6]), unsolved_funcs.keys()):
        #                 unsolved_funcs[(edge[4], edge[5], strip_tag(edge[6]))] = [(edge[0], edge[1], strip_tag(edge[2]), edge[3])]
        #             else:
        #                 unsolved_funcs[(edge[4], edge[5], strip_tag(edge[6]))].append((edge[0], edge[1], strip_tag(edge[2]), edge[3]))
        #     for key in unsolved_funcs:
        #         solving_funcs(key[2], unsolved_funcs, impacted_terms)
        #     cleaned_impacted_terms = [term for term in impacted_terms if term[2] != slot and slot_exists(term[2], slots)]
        #     if len(cleaned_impacted_terms) > 0:
        #         ann_impact_res.append({'filename': filename, 'line': line, 'offset': offset, 'slot': slot, 'annotation_impact': len(cleaned_impacted_terms),
        #                'terms_with_potential_type_updates': cleaned_impacted_terms})
        # sorted_data = sorted(ann_impact_res, key=lambda x: x['annotation_impact'], reverse=True)
        # with open(filename.replace('.py', f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_ai"), 'w') as f:
        #     for ann_impact in sorted_data:
        #         print(ann_impact, file=f)

    # try:
    #     G = nx.DiGraph()
    #     G.add_edges_from(edges_clean)
    #     plt.figure(figsize=(15, 10))
    #     pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
    #     nx.draw(G, pos, with_labels=True, node_color='skyblue', node_size=500, edge_color='black', linewidths=1,
    #             font_size=10, arrowsize=10)
    #     plt.show()
    # except ImportError as e:
    #     print("Error: pygraphviz is not installed or not working properly.")
    #     print(e)
    # except Exception as e:
    #     print("An error occurred:")
    #     print(e)
