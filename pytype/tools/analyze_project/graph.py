import networkx as nx
import matplotlib.pyplot as plt


def clean_edges(edges):
    ret = []
    for u, v in edges:
        if v[0] == 'v' and v[1:].isdigit():
            continue
        if u is None:
            u = 'None'
        if v is None:
            v = 'None'
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

def call_opcode_handler(edges, element):
    for edge in edges:
        if edge[1] == f"v{element['funcv'].id}":
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
             or opcode_list[i]['opcode'] == 'LOAD_GLOBAL')
                and opcode_list[i]['value_data'] == element['value_data']):
            for edge in edges:
                if edge[1] == opcode_list[i]['value_id']:
                    edge[1] = element['name']
            break

def draw_type_inference_graph(opcode_list):
    edges = []
    for element in opcode_list:
        if element['opcode'] == 'LOAD_CONST':
            edges.append([element['raw_const'], element['value_id']])
        elif element['opcode'] == 'LOAD_NAME':
            edges.append([element['name'], element['value_id']])
        elif element['opcode'] == 'LOAD_FAST':
            _store_fast(opcode_list, element, edges)
            edges.append([element['name'], element['value_id']])
        elif element['opcode'] == 'LOAD_FOLDED_CONST':
            edges.append([element['raw_const'], element['value_id']])
        elif element['opcode'] == 'BINARY_OP':
            for edge in edges:
                if edge[1] == element['x_id'] or edge[1] == element['y_id']:
                    edge[1] = element['ret_id']
        elif element['opcode'] == 'STORE_NAME':
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
            obj_name = find_obj_name_via_data(opcode_list, element)
            edges.append([obj_name, f"{obj_name}.{element['name']}"])
            edges.append([f"{obj_name}.{element['name']}", element['val_id']])
        elif element['opcode'] == 'CALL':
            call_opcode_handler(edges, element)
        elif element['opcode'] == 'DICT_MERGE':
            for edge in edges:
                if edge[1] == element['update_id']:
                    edge[1] = element['target_id']

    edges_clean = clean_edges(edges)

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
