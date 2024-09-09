import networkx as nx
import matplotlib.pyplot as plt
from pytype.abstract._classes import PyTDClass, ParameterizedClass, TupleClass
from pytype.abstract._singletons import Unsolvable

opcode_list = []  # recording all opcodes to draw the type inference graph

def clean_edges(edges):
    ret = []
    for u, v in edges:
        if v[0] == 'v' and v[1:].isdigit():
            continue
        if u is None:
            u = 'None'
        if v is None:
            v = 'None'
        if u == '':
            u = "''"
        if v == '':
            v = "''"
        if u == '\\':
            u = '\\\\'
        if v == '\\':
            v = '\\\\'
        if v == '__qualname__' or v == '__doc__' or v == '__module__' or u == v:
            continue
        ret.append([u, v])
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
                if edge[1] == opcode_list[i]['ret_id']:
                    obj_name = edge[0]
        elif ((opcode_list[i]['opcode'] == 'LOAD_CONST' or opcode_list[i]['opcode'] == 'LOAD_FAST'
             or opcode_list[i]['opcode'] == 'LOAD_NAME' or opcode_list[i]['opcode'] == 'LOAD_FOLDED_CONST'
             or opcode_list[i]['opcode'] == 'LOAD_GLOBAL') and opcode_list[i]['value_id'] == element['obj_id']):
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
                if edge[1] ==opcode_list[i]['value_id']:
                    obj_name = edge[0]
    return obj_name

def call_opcode_handler(edges, element, opcode_list):
    last_opcode = opcode_list[opcode_list.index(element)-1]
    if last_opcode['opcode'] == 'RETURN_VALUE' and last_opcode['value_data'] == element['ret'].data:
        for edge in edges:
            if edge[1] == last_opcode['value_id']:
                edge[1] = f"v{element['ret'].id}"
    else:
        for edge in edges:
            if edge[1] == f"v{element['funcv'].id}":
                if edge[0].split('.')[-1] == 'replace':
                    for e in edges[::-1]:
                        if e[1] == edge[0]:
                            e[1] = f"v{element['ret'].id}"
                            return
                edge[1] = f"v{element['ret'].id}"
        if element['posargs']:
            for arg in element['posargs']:
                for edge in edges:
                    if edge[1] == f"v{arg.id}":
                        edge[1] = f"v{element['ret'].id}"
        if element['namedargs']:
            for k, v in element['namedargs'].items():
                for edge in edges:
                    if edge[1] == f"v{v.id}":
                        edge[1] = f"v{element['ret'].id}"
        if element['starargs']:
            for edge in edges:
                if edge[1] == f"v{element['starargs'].id}":
                    print("DEBUG")
                    edge[1] = f"v{element['ret'].id}"
        if element['starstarargs']:
            for edge in edges:
                if edge[1] == f"v{element['starstarargs'].id}":
                    edge[1] = f"v{element['ret'].id}"

def _store_fast(opcode_list, element, edges):
    for i in range(opcode_list.index(element) - 1, -1, -1):
        if ((opcode_list[i]['opcode'] == 'LOAD_CONST' or opcode_list[i]['opcode'] == 'LOAD_FAST'
             or opcode_list[i]['opcode'] == 'LOAD_NAME' or opcode_list[i]['opcode'] == 'LOAD_FOLDED_CONST'
             or opcode_list[i]['opcode'] == 'LOAD_GLOBAL') and opcode_list[i]['value_data'] == element['value_data']):
            for edge in edges:
                if edge[1] == opcode_list[i]['value_id']:
                    edge[1] = element['name']
            break

def draw_type_inference_graph(opcode_list):
    print('====opcodes====')
    for opcode in opcode_list:
        print(opcode)
    print('====opcodes====')
    edges = []
    for element in opcode_list:
        if element['opcode'] == 'LOAD_CONST':
            edges.append([element['raw_const'], element['value_id']])
        elif element['opcode'] == 'LOAD_NAME' or element['opcode'] == 'LOAD_GLOBAL':
            edges.append([element['name'], element['value_id']])
        elif element['opcode'] == 'LOAD_FAST':
            exist = False
            for edge in edges:
                if edge[1] == element['name']:
                    exist = True
            if not exist:
                _store_fast(opcode_list, element, edges)
            edges.append([element['name'], element['value_id']])
        elif element['opcode'] == 'LOAD_FOLDED_CONST':
            edges.append([element['raw_const'], element['value_id']])
        elif element['opcode'] == 'BINARY_OP':
            if element['name'] == '__sub__':
                pass
            if element['name'] == '__getitem__':
                x_name = ''
                y_name = ''
                for edge in edges:
                    if edge[1] == element['x_id']:
                        x_name = edge[0]
                    if edge[1] == element['y_id']:
                        y_name = edge[0]
                if y_name != '':
                    for edge in edges:
                        if edge[1] == element['x_id'] or edge[1] == element['y_id']:
                            edge[1] = f"{x_name}[{y_name}]"
                    edges.append([f"{x_name}[{y_name}]", element['ret_id']])
                else:
                    for edge in edges:
                        if edge[1] == element['x_id'] or edge[1] == element['y_id']:
                            edge[1] = element['ret_id']
            else:
                for edge in edges:
                    if edge[1] == element['x_id'] or edge[1] == element['y_id']:
                        edge[1] = element['ret_id']
        elif element['opcode'] == 'STORE_NAME':
            if 'annotation' in element:
                if edges[-1][1] == 'return':
                    edges[-1][1] = 'v0'
                edges.append([element['annotation'], element['name']])
            else:
                found = False
                for edge in edges:
                    if edge[1] == element['value_id']:
                        edge[1] = element['name']
                        found = True
                if not found:
                    _store_fast(opcode_list, element, edges)
        elif element['opcode'] == 'STORE_SUBSCR':
            obj_name = find_obj_name_via_id(opcode_list, element)
            for edge in edges:
                if edge[1] == element['key_id'] or edge[1] == element['value_id']:
                    if obj_name != '':
                        edge[1] = obj_name
                    else:
                        edge[1] = element['obj_id']
        elif element['opcode'] == 'STORE_ATTR':
            obj_name = find_obj_name_via_id(opcode_list, element)
            for edge in edges:
                if edge[1] == element['val_id']:
                    edge[1] = f"{obj_name}.{element['name']}"
        elif element['opcode'] == 'LOAD_ATTR' or element['opcode'] == 'LOAD_METHOD':
            obj_name = find_obj_name_via_id_SUBSCR(opcode_list, element, edges)
            if obj_name == '':
                obj_name = find_obj_name_via_data(opcode_list, element)
            if element['name'] == 'append':
                edges.append([obj_name, element['value_id']])
            else:
                for edge in edges:
                    if edge[1] == element['obj_id']:
                        edge[1] = f"{obj_name}.{element['name']}"
                edges.append([f"{obj_name}.{element['name']}", element['value_id']])
        elif element['opcode'] == 'CALL':
            call_opcode_handler(edges, element, opcode_list)
        elif element['opcode'] == 'APPEND':
            l = ''
            new_item = ''
            for edge in edges:
                if edge[1] == f"v{element['funcv'].id}":
                    l = edge[0]
                if edge[1] == f"v{element['posargs'][0].id}":
                    new_item = edge[0]
            edges.append([new_item, l])
        elif element['opcode'] == 'DICT_MERGE' or element['opcode'] == 'LIST_EXTEND':
            for edge in edges:
                if edge[1] == element['update_id']:
                    edge[1] = element['target_id']
        elif element['opcode'] == 'GET_ITER':
            for edge in edges:
                if edge[1] == element['seq_id']:
                    edge[1] = element['itr_id']
        elif element['opcode'] == 'FOR_ITER':
            for edge in edges:
                if edge[1] == element['iter_id']:
                    edge[1] = element['func_id']
        elif element['opcode'] == 'UNPACK_SEQUENCE':
            for edge in edges:
                if edge[1] == element['seq_id']:
                    edge[1] = f"iter_{element['seq_id']}"
            for value_id in element['value_ids']:
                edges.append([f"iter_{element['seq_id']}", value_id])
        elif element['opcode'] == 'RESUME':
            for opcode in opcode_list:
                if opcode['opcode'] == 'MAKE_FUNCTION' and f"Function:{opcode['func_name']}" == element['state_node_name']:
                    for id, ann in opcode['annot'].items():
                        if isinstance(ann, PyTDClass):
                            edges.append([ann.name, id])
                        elif isinstance(ann, ParameterizedClass):
                            base_cls = ''
                            param_type = ''
                            if isinstance(ann.base_cls, PyTDClass):
                                base_cls = ann.base_cls.name
                            if isinstance(ann._formal_type_parameters['_T'], PyTDClass):
                                param_type = ann._formal_type_parameters['_T'].name
                            elif isinstance(ann._formal_type_parameters['_T'], Unsolvable):
                                param_type = 'Any'
                            if base_cls != '' and param_type != '':
                                edges.append([f"{base_cls}[{param_type}]", id])
                            else:
                                edges.append([ann, id])
                        else:
                            edges.append([ann, id])
        elif element['opcode'] == 'RETURN_VALUE':
            for edge in edges:
                if edge[1] == element['value_id']:
                    edge[1] = 'return'
        elif element['opcode'] == 'COMPARE_OP':
            for edge in edges:
                if edge[1] == element['x_id'] or edge[1] == element['y_id']:
                    edge[1] = element['ret_id']
        elif element['opcode'] == 'BUILD_STRING':
            edges.append(['str', element['val_id']])
    edges_clean = clean_edges(edges)
    print('====edges====')
    for edge in edges_clean:
        print(edge)
    print('====edges====')
    try:
        G = nx.DiGraph()
        G.add_edges_from(edges_clean)
        plt.figure(figsize=(15, 10))
        pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
        nx.draw(G, pos, with_labels=True, node_color='skyblue', node_size=500, edge_color='black', linewidths=1,
                font_size=10, arrowsize=10)
        plt.show()
    except ImportError as e:
        print("Error: pygraphviz is not installed or not working properly.")
        print(e)
    except Exception as e:
        print("An error occurred:")
        print(e)
