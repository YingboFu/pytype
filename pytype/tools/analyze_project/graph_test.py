from pytype.tests import test_base
from pytype.tools.analyze_project.graph import opcode_list, draw_type_inference_graph


def has_edge(edges, from_line, from_offset, from_name, to_line, to_offset, to_name):
    for edge in edges:
        if (edge[0] == from_line and edge[1] == from_offset and edge[2] == from_name
                and edge[4] == to_line and edge[5] == to_offset and edge[6] == to_name):
            return True
    return False


class TypeInferenceGraphTest(test_base.BaseTest):

    def test_basic_assignment(self):
        opcode_list.clear()
        source = """
        
            a = 1
            b = {1: 'foo'}
            c = [1, 2, 3]
            d = 3, 4
            """
        self.Infer(source)
        edges = draw_type_inference_graph(opcode_list)
        self.assertTrue(has_edge(edges, 2, 4, '<CONST> 1', 2, 0, '<IDENT> a'))
        self.assertTrue(has_edge(edges, 3, 4, "<CONST> {1: 'foo'}", 3, 0, '<IDENT> b'))
        self.assertTrue(has_edge(edges, 4, 4, '<CONST> [1, 2, 3]', 4, 0, '<IDENT> c'))
        self.assertTrue(has_edge(edges, 5, 4, '<CONST> (3, 4)', 5, 0, '<IDENT> d'))

    def test_self_edge(self):
        opcode_list.clear()
        source = """

            d = 3, 4
            x = d
            """
        self.Infer(source)
        edges = draw_type_inference_graph(opcode_list)
        self.assertTrue(has_edge(edges, 2, 4, '<CONST> (3, 4)', 2, 0, '<IDENT> d'))
        self.assertTrue(has_edge(edges, 2, 0, '<IDENT> d', 3, 4, '<IDENT> d'))
        self.assertTrue(has_edge(edges, 3, 4, '<IDENT> d', 3, 0, '<IDENT> x'))

    def test_user_defined_function_call(self):
        # todo: arg offset and ret line and offset
        # todo: Edges in TypeInferenceGraph shouldn't be sorted by line,
        #  which might Lower Annotation Impact across user-defined function calls.
        #  Try #1 not sorting it and #2 traversing the graph twice to see if
        #  it improves the performance significantly
        opcode_list.clear()
        source = """
    
            def my_sum(a, b):
                return a + b
            
            x = 3
            y = 4
            res = my_sum(x, y)
            """
        self.Infer(source)
        edges = draw_type_inference_graph(opcode_list)
        self.assertTrue(has_edge(edges, 5, 4, '<CONST> 3', 5, 0, '<IDENT> x'))
        self.assertTrue(has_edge(edges, 6, 4, '<CONST> 4', 6, 0, '<IDENT> y'))
        self.assertTrue(has_edge(edges, 5, 0, '<IDENT> x', 7, 13, '<IDENT> x'))
        self.assertTrue(has_edge(edges, 6, 0, '<IDENT> y', 7, 16, '<IDENT> y'))
        self.assertTrue(has_edge(edges, 7, 13, '<IDENT> x', 2, 0, '<PARAM> my_sum.a'))
        self.assertTrue(has_edge(edges, 7, 16, '<IDENT> y', 2, 0, '<PARAM> my_sum.b'))
        self.assertTrue(has_edge(edges, 2, 0, '<PARAM> my_sum.a', 3, 11, '<IDENT> my_sum.a'))
        self.assertTrue(has_edge(edges, 2, 0, '<PARAM> my_sum.b', 3, 15, '<IDENT> my_sum.b'))
        self.assertTrue(has_edge(edges, 3, 11, '<IDENT> my_sum.a', 3, 4, '<RET> my_sum.return'))
        self.assertTrue(has_edge(edges, 3, 15, '<IDENT> my_sum.b', 3, 4, '<RET> my_sum.return'))
        self.assertTrue(has_edge(edges, 3, 4, '<RET> my_sum.return', 7, 0, '<IDENT> res'))

    def test_external_function_and_method_call(self):
        opcode_list.clear()
        source = """
        
        def to_str(value):
            return str(value).strip()
        """
        self.Infer(source)
        edges = draw_type_inference_graph(opcode_list)
        self.assertTrue(has_edge(edges, 2, 0, '<TYPE> Noanno', 2, 0, '<PARAM> to_str.value'))
        self.assertTrue(has_edge(edges, 3, 11, '<FUNC> to_str.str', 3, 11, '<IDENT> to_str.str(value)'))
        self.assertTrue(has_edge(edges, 2, 0, '<PARAM> to_str.value', 3, 15, '<IDENT> to_str.value'))
        self.assertTrue(has_edge(edges, 3, 15, '<ARG> to_str.value', 3, 11, '<IDENT> to_str.str(value)'))
        self.assertTrue(has_edge(edges, 3, 11, '<IDENT> to_str.str(value)', 3, 11, '<IDENT> to_str.str(value).strip'))
        self.assertTrue(has_edge(edges, 3, 11, '<FUNC> to_str.str(value).strip', 3, 11, '<IDENT> to_str.str(value).strip()'))
        self.assertTrue(has_edge(edges, 3, 11, '<IDENT> to_str.str(value).strip()', 3, 4, '<RET> to_str.return'))
