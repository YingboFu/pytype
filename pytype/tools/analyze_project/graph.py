import networkx as nx
import matplotlib.pyplot as plt

def clean_edges(edges):
    ret = []
    for u, v in edges:
        if v[0] == 'v' and v[1:].isdigit():
            continue
        ret.append([u, v])
    return ret

def draw_type_inference_graph(opcode_queue):
    edges = []
    while not opcode_queue.empty():
        element = opcode_queue.get()
        if element['opcode'] == 'LOAD_CONST':
            edges.append([element['raw_const'], element['value_id']])
        elif element['opcode'] == 'STORE_NAME':
            for edge in edges:
                if edge[1] == element['value_id']:
                    edge[1] = element['name']
        elif element['opcode'] == 'LOAD_NAME':
            edges.append([element['name'], element['value_id']])
        elif element['opcode'] == 'BINARY_OP':
            for edge in edges:
                if edge[1] == element['x_id'] or edge[1] == element['y_id']:
                    edge[1] = element['name']
            edges.append([element['name'], element['ret_id']])
        elif element['opcode'] == 'STORE_NAME':
            for edge in edges:
                if edge[1] == element['value_id']:
                    edge[1] = element['name']

    edges_clean = clean_edges(edges)

    G = nx.DiGraph()
    G.add_edges_from(edges_clean)
    pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
    nx.draw(G, pos, with_labels=True, node_color='skyblue', node_size=2000, edge_color='black', linewidths=1,
            font_size=15, arrowsize=20)

    plt.show()
