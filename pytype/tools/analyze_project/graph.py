import networkx as nx
import matplotlib.pyplot as plt


def clean_edges(edges):
    ret = []
    for u, v in edges:
        if v[0] == 'v' and v[1:].isdigit():
            continue
        ret.append([u, v])
    return ret


def _store_fast(opcode_list, element, edges):
    for i in range(opcode_list.index(element) - 1, -1, -1):
        if ((opcode_list[i]['opcode'] == 'LOAD_CONST' or opcode_list[i]['opcode'] == 'LOAD_FAST'
             or opcode_list[i]['opcode'] == 'LOAD_NAME' or opcode_list[i]['opcode'] == 'LOAD_FOLDED_CONST')
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
                    edge[1] = element['name']
            edges.append([element['name'], element['ret_id']])
        elif element['opcode'] == 'STORE_NAME':
            for edge in edges:
                if edge[1] == element['value_id']:
                    edge[1] = element['name']
            _store_fast(opcode_list, element, edges)
        elif element['opcode'] == 'STORE_SUBSCR':
            obj_name = ''
            for edge in edges[::-1]:
                if edge[1] == element['obj_id']:
                    obj_name = edge[0]
                    break
            for edge in edges:
                if edge[1] == element['key_id'] or edge[1] == element['value_id']:
                    if obj_name != '':
                        edge[1] = obj_name
                    else:
                        edge[1] = element['obj_id']

    edges_clean = clean_edges(edges)

    try:
        G = nx.DiGraph()
        G.add_edges_from(edges_clean)
        pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
        nx.draw(G, pos, with_labels=True, node_color='skyblue', node_size=2000, edge_color='black', linewidths=1,
                font_size=15, arrowsize=20)

        plt.show()
    except ImportError as e:
        print("Error: pygraphviz is not installed or not working properly.")
        print(e)
    except Exception as e:
        print("An error occurred:")
        print(e)
