import networkx as nx
import matplotlib.pyplot as plt
from pytype.abstract._classes import PyTDClass, ParameterizedClass, TupleClass
from pytype.abstract._singletons import Unsolvable
import re

opcode_list = []  # recording all opcodes to draw the type inference graph

def clean_edges(edges):
    ret = []
    for l, u, v in edges:
        # removing all type constructions
        if l == 1:
            continue
        if v[0] == 'v' and v[1:].isdigit():
            continue
        if strip_tag(v) == '__qualname__' or strip_tag(v) == '__doc__' or strip_tag(v) == '__module__' or strip_tag(u) == strip_tag(v):
            continue
        ret.append([l, u, v])
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
    for i in range(opcode_list.index(element) - 1, -1, -1):
        if opcode_list[i]['opcode'] == 'BINARY_OP' and opcode_list[i]['ret_id'] == element['obj_id']:
            for edge in edges:
                if edge[2] == opcode_list[i]['ret_id']:
                    obj_name = strip_tag(edge[1])
        elif opcode_list[i]['opcode'] == 'CALL' and f"v{opcode_list[i]['ret'].id}" == element['obj_id']:
            for edge in edges:
                if edge[2] == f"v{opcode_list[i]['ret'].id}":
                    if obj_name == '':
                        obj_name = f"{strip_tag(edge[1])}()"
                    else:
                        ridx = obj_name.rfind(')')
                        if ridx != -1:
                            if obj_name[ridx - 1] == '(':
                                obj_name = obj_name[:ridx] + f"{strip_tag(edge[1])}" + obj_name[ridx:]
                            else:
                                obj_name = obj_name[:ridx] + f",{strip_tag(edge[1])}" + obj_name[ridx:]
        elif ((opcode_list[i]['opcode'] == 'LOAD_CONST' or opcode_list[i]['opcode'] == 'LOAD_FAST'
             or opcode_list[i]['opcode'] == 'LOAD_NAME' or opcode_list[i]['opcode'] == 'LOAD_FOLDED_CONST'
             or opcode_list[i]['opcode'] == 'LOAD_GLOBAL' or opcode_list[i]['opcode'] == 'LOAD_CLOSURE')
              and opcode_list[i]['value_id'] == element['obj_id']):
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
                if edge[2] ==opcode_list[i]['value_id']:
                    obj_name = strip_tag(edge[1])
    return obj_name

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

def call_opcode_handler(edges, element, opcode_list):
    last_opcode = opcode_list[opcode_list.index(element)-1]
    func_name = find_func_name(opcode_list, element)
    if func_name is not None and (func_name.endswith('<listcomp>') or func_name.endswith('<genexpr>')):
        # handling listcomp and genexpr
        last_yield_value_id = find_last_yield_value_id(opcode_list, element)
        edges.append([element['line'], f"<ITER> {last_yield_value_id}", f"v{element['ret'].id}"])
    elif func_name is not None and func_name.endswith('<dictcomp>'):
        # handling dictcomp
        map_id = find_map_id(opcode_list, element)
        for edge in edges:
            if edge[2] == map_id:
                edge[0] = element['line']
                edge[2] = f"<DICT> v{element['ret'].id}"
        edges.append([element['line'], f"<DICT> v{element['ret'].id}", f"v{element['ret'].id}"])
    elif last_opcode['opcode'] == 'RETURN_VALUE' and last_opcode['value_data'] == element['ret'].data:
        for edge in edges:
            if edge[2] == last_opcode['value_id']:
                edge[0] = element['line']
                edge[2] = f"v{element['ret'].id}"
    else:
        for edge in edges:
            if edge[2] == f"v{element['funcv'].id}":
                if edge[1].split('.')[-1] == 'replace':
                    for e in edges[::-1]:
                        if e[2] == edge[1]:
                            e[0] = element['line']
                            e[2] = f"v{element['ret'].id}"
                            return
                edge[0] = element['line']
                if last_opcode['opcode'] != 'FOR_ITER' or last_opcode['func_id'] != f"v{element['funcv'].id}":
                    edge[1] = f"<FUNC> {strip_tag(edge[1])}"
                edge[2] = f"v{element['ret'].id}"
        if element['posargs']:
            for arg in element['posargs']:
                for edge in edges:
                    if edge[2] == f"v{arg.id}":
                        edge[0] = element['line']
                        if not edge[1].startswith('<FUNC>'):
                            edge[1] = f"<PARAM> {strip_tag(edge[1])}"
                        edge[2] = f"v{element['ret'].id}"
        if element['namedargs']:
            for k, v in element['namedargs'].items():
                for edge in edges:
                    if edge[2] == f"v{v.id}":
                        edge[0] = element['line']
                        if not edge[1].startswith('FUNC'):
                            edge[1] = f"<PARAM> {strip_tag(edge[1])}"
                        edge[2] = f"v{element['ret'].id}"
        if element['starargs']:
            for edge in edges:
                if edge[2] == f"v{element['starargs'].id}":
                    edge[0] = element['line']
                    if not edge[1].startswith('FUNC'):
                        edge[1] = f"<PARAM> {strip_tag(edge[1])}"
                    edge[2] = f"v{element['ret'].id}"
        if element['starstarargs']:
            for edge in edges:
                if edge[2] == f"v{element['starstarargs'].id}":
                    edge[0] = element['line']
                    if not edge[1].startswith('FUNC'):
                        edge[1] = f"<PARAM> {strip_tag(edge[1])}"
                    edge[2] = f"v{element['ret'].id}"

def _store_fast(opcode_list, element, edges):
    for i in range(opcode_list.index(element) - 1, -1, -1):
        if ((opcode_list[i]['opcode'] == 'LOAD_CONST' or opcode_list[i]['opcode'] == 'LOAD_FAST'
             or opcode_list[i]['opcode'] == 'LOAD_NAME' or opcode_list[i]['opcode'] == 'LOAD_FOLDED_CONST'
             or opcode_list[i]['opcode'] == 'LOAD_GLOBAL') and opcode_list[i]['value_data'] == element['value_data']):
            for edge in edges:
                if edge[2] == opcode_list[i]['value_id']:
                    edge[0] = element['line']
                    edge[2] = f"<IDENT> {element['name']}"
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

def draw_type_inference_graph(opcode_list):
    opcode_list = _pre_process_opcodes(opcode_list)
    print('====opcodes====')
    for opcode in opcode_list:
        print(opcode)
    print('====opcodes====')
    edges = []
    for element in opcode_list:
        if element['opcode'] == 'LOAD_CONST':
            edges.append([element['line'], f"<CONST> {element['raw_const']}", element['value_id']])
        elif element['opcode'] == 'LOAD_NAME' or element['opcode'] == 'LOAD_GLOBAL' or element['opcode'] == 'LOAD_CLOSURE':
            edges.append([element['line'], f"<IDENT> {element['name']}", element['value_id']])
        elif element['opcode'] == 'LOAD_FAST':
            if re.fullmatch(r"\.\d+", element['name']):
                # Variables with a ".n" naming scheme are things like iterators for list comprehensions
                for i in range(opcode_list.index(element) - 1, -1, -1):
                    if opcode_list[i]['opcode'] == 'GET_ITER':
                        for edge in edges:
                            if edge[2] == opcode_list[i]['itr_id']:
                                edge[0] = element['line']
                                edge[2] = element['value_id']
                        break
            else:
                exist = False
                for edge in edges:
                    if strip_tag(edge[2]) == element['name']:
                        exist = True
                if not exist:
                    _store_fast(opcode_list, element, edges)
                edges.append([element['line'], f"<IDENT> {element['name']}", element['value_id']])
        elif element['opcode'] == 'LOAD_FOLDED_CONST':
            edges.append([element['line'], f"<CONST> {element['raw_const']}", element['value_id']])
        elif element['opcode'] == 'BINARY_OP':
            if element['name'] == '__sub__':
                pass
            if element['name'] == '__getitem__':
                x_name = ''
                y_name = ''
                for edge in edges:
                    if edge[2] == element['x_id']:
                        if x_name == '':
                            if edge[1].startswith('<FUNC>'):
                                x_name = f"{strip_tag(edge[1])}()"
                            else:
                                x_name = strip_tag(edge[1])
                        else:
                            if edge[1].startswith('<PARAM>'):
                                ridx = x_name.rfind(')')
                                if ridx != -1:
                                    if x_name[ridx - 1] == '(':
                                        x_name = x_name[:ridx] + f"{strip_tag(edge[1])}" + x_name[ridx:]
                                    else:
                                        x_name = x_name[:ridx] + f", {strip_tag(edge[1])}" + x_name[ridx:]
                    if edge[2] == element['y_id']:
                        y_name = strip_tag(edge[1])
                if y_name != '':
                    for edge in edges:
                        if edge[2] == element['x_id'] or edge[2] == element['y_id']:
                            edge[0] = element['line']
                            edge[2] = f"<IDENT> {x_name}[{y_name}]"
                    edges.append([element['line'], f"<IDENT> {x_name}[{y_name}]", element['ret_id']])
                else:
                    for edge in edges:
                        if edge[2] == element['x_id'] or edge[2] == element['y_id']:
                            edge[0] = element['line']
                            edge[2] = element['ret_id']
            else:
                for edge in edges:
                    if edge[2] == element['x_id'] or edge[2] == element['y_id']:
                        edge[0] = element['line']
                        edge[2] = element['ret_id']
        elif element['opcode'] == 'STORE_NAME':
            if 'annotation' in element:
                if strip_tag(edges[-1][2]) == 'return':
                    edges[-1][0] = element['line']
                    edges[-1][2] = 'v0'
                edges.append([element['line'], f"<TYPE> {element['annotation']}", f"<IDENT> {element['name']}"])
            else:
                found = False
                for edge in edges:
                    if edge[2] == element['value_id']:
                        edge[0] = element['line']
                        edge[2] = f"<IDENT> {element['name']}"
                        found = True
                if not found:
                    _store_fast(opcode_list, element, edges)
        elif element['opcode'] == 'STORE_SUBSCR':
            obj_name = find_obj_name_via_id(opcode_list, element)
            for edge in edges:
                if edge[2] == element['key_id'] or edge[2] == element['value_id']:
                    edge[0] = element['line']
                    if obj_name != '':
                        edge[2] = f"<IDENT> {obj_name}"
                    else:
                        edge[2] = element['obj_id']
        elif element['opcode'] == 'STORE_ATTR':
            obj_name = find_obj_name_via_id(opcode_list, element)
            for edge in edges:
                if edge[2] == element['val_id']:
                    edge[0] = element['line']
                    edge[2] = f"<IDENT> {obj_name}.{element['name']}"
        elif element['opcode'] == 'LOAD_ATTR' or element['opcode'] == 'LOAD_METHOD':
            obj_name = find_obj_name_via_id_SUBSCR(opcode_list, element, edges)
            if obj_name == '':
                obj_name = find_obj_name_via_data(opcode_list, element)
            if element['name'] == 'append':
                edges.append([element['line'], f"<IDENT> {obj_name}", element['value_id']])
            else:
                for edge in edges:
                    if edge[2] == element['obj_id']:
                        edge[0] = element['line']
                        edge[2] = f"<IDENT> {obj_name}.{element['name']}"
                edges.append([element['line'], f"<IDENT> {obj_name}.{element['name']}", element['value_id']])
        elif element['opcode'] == 'CALL':
            call_opcode_handler(edges, element, opcode_list)
        elif element['opcode'] == 'APPEND':
            l = ''
            new_item = ''
            for edge in edges:
                if edge[2] == f"v{element['funcv'].id}":
                    l = edge[1]
                if edge[2] == f"v{element['posargs'][0].id}":
                    new_item = edge[1]
            edges.append([element['line'], new_item, l])
        elif element['opcode'] == 'DICT_MERGE' or element['opcode'] == 'LIST_EXTEND':
            for edge in edges:
                if edge[2] == element['update_id']:
                    edge[0] = element['line']
                    edge[2] = element['target_id']
        elif element['opcode'] == 'GET_ITER':
            for edge in edges:
                if edge[2] == element['seq_id']:
                    edge[0] = element['line']
                    edge[2] = element['itr_id']
        elif element['opcode'] == 'FOR_ITER':
            for edge in edges:
                if edge[2] == element['iter_id']:
                    edge[0] = element['line']
                    edge[2] = element['func_id']
        elif element['opcode'] == 'UNPACK_SEQUENCE':
            for edge in edges:
                if edge[2] == element['seq_id']:
                    edge[0] = element['line']
                    edge[2] = f"<ITER> {element['seq_id']}"
            for value_id in element['value_ids']:
                edges.append([element['line'], f"<ITER> {element['seq_id']}", value_id])
        elif element['opcode'] == 'RESUME':
            for opcode in opcode_list:
                if opcode['opcode'] == 'MAKE_FUNCTION' and f"Function:{opcode['func_name']}" == element['state_node_name']:
                    for k, ann in opcode['annot'].items():
                        lidx = repr(ann).find("'")
                        ridx = repr(ann).rfind("'")
                        ann_str = repr(ann)[lidx + 1: ridx]
                        if k != 'return':
                            edges.append([opcode['line'], f"<TYPE> {ann_str}", f"<PARAM> {k}"])
                        else:
                            edges.append([opcode['line'], f"<TYPE> {ann_str}", f"<RET> {k}"])
        elif element['opcode'] == 'RETURN_VALUE':
            if element['state_node_name'].startswith('Function:'):
                for edge in edges:
                    if edge[2] == element['value_id']:
                        edge[0] = element['line']
                        edge[2] = '<RET> return'
            else:
                if opcode_list.index(element) + 2 < len(opcode_list):
                    next_resume = opcode_list[opcode_list.index(element) + 2]
                    if next_resume['opcode'] == 'RESUME' and next_resume['state_node_name'].startswith('Function:'):
                        for edge in edges:
                            if edge[2] == element['value_id']:
                                edge[0] = element['line']
                                edge[2] = '<RET> return'
        elif element['opcode'] == 'COMPARE_OP':
            for edge in edges:
                if edge[2] == element['x_id'] or edge[2] == element['y_id']:
                    edge[0] = element['line']
                    edge[2] = element['ret_id']
        elif element['opcode'] == 'BUILD_STRING':
            edges.append([element['line'], '<TYPE> str', element['val_id']])
        elif element['opcode'] == 'BUILD_TUPLE':
            tuple_str = ''
            elt_ids = [f"v{item.id}" for item in element['elts']]
            for edge in edges:
                if edge[2] in elt_ids:
                    if tuple_str == '':
                        if edge[1].startswith('<FUNC>'):
                            tuple_str = f"{strip_tag(edge[1])}()"
                        else:
                            tuple_str = strip_tag(edge[1])
                    else:
                        if edge[1].startswith('<FUNC>'):
                            tuple_str = tuple_str + ", " + f"{strip_tag(edge[1])}()"
                        elif edge[1].startswith('<PARAM>'):
                            ridx = tuple_str.rfind(')')
                            if ridx != -1:
                                if tuple_str[ridx - 1] == '(':
                                    tuple_str = tuple_str[:ridx] + f"{strip_tag(edge[1])}" + tuple_str[ridx:]
                                else:
                                    tuple_str = tuple_str[:ridx] + f", {strip_tag(edge[1])}" + tuple_str[ridx:]
                        else:
                            tuple_str = tuple_str + ", " + strip_tag(edge[1])
            for edge in edges:
                if edge[2] in elt_ids:
                    edge[0] = element['line']
                    edge[2] = f"<TUPLE> {tuple_str}"
            edges.append([element['line'], f"<TUPLE> {tuple_str}", element['value_id']])
        elif element['opcode'] == 'YIELD_VALUE':
            for edge in edges:
                if edge[2] == element['yield_id']:
                    edge[0] = element['line']
                    edge[2] = f"<ITER> {element['send_id']}"
        elif element['opcode'] == 'MAP_ADD':
            for edge in edges:
                if edge[2] == element['key_id'] or edge[2] == element['value_id']:
                    edge[0] = element['line']
                    edge[2] = element['map_id']

    edges_clean = clean_edges(edges)
    print('====edges====')
    for edge in edges_clean:
        print(edge)
    print('====edges====')
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
