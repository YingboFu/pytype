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

    def test_for_loop_and_append(self):
        opcode_list.clear()
        source = """

        def _win32_process_path_backslash(value):
            result = []
            for ix, char in enumerate(value):
                result.append(char)
            return result
        """
        self.Infer(source)
        edges = draw_type_inference_graph(opcode_list)
        self.assertTrue(has_edge(edges, 2, 0, '<TYPE> Noanno', 2, 0, '<PARAM> _win32_process_path_backslash.value'))
        self.assertTrue(has_edge(edges, 3, 13, '<CONST> []', 3, 4, '<IDENT> _win32_process_path_backslash.result'))
        self.assertTrue(has_edge(edges, 4, 20, '<FUNC> _win32_process_path_backslash.enumerate', 4, 20, '<IDENT> _win32_process_path_backslash.enumerate(value)'))
        self.assertTrue(has_edge(edges, 2, 0, '<PARAM> _win32_process_path_backslash.value', 4, 30, '<IDENT> _win32_process_path_backslash.value'))
        self.assertTrue(has_edge(edges, 4, 30, '<ARG> _win32_process_path_backslash.value', 4, 20, '<IDENT> _win32_process_path_backslash.enumerate(value)'))
        self.assertTrue(has_edge(edges, 4, 20, '<IDENT> _win32_process_path_backslash.enumerate(value)', 4, 8, '<ITER> v573'))
        self.assertTrue(has_edge(edges, 4, 8, '<ITER> v573', 4, 12, '<IDENT> _win32_process_path_backslash.char'))
        self.assertTrue(has_edge(edges, 4, 8, '<ITER> v573', 4, 8, '<IDENT> _win32_process_path_backslash.ix'))
        self.assertTrue(has_edge(edges, 3, 4, '<IDENT> _win32_process_path_backslash.result', 5, 8, '<IDENT> _win32_process_path_backslash.result'))
        self.assertTrue(has_edge(edges, 4, 12, '<IDENT> _win32_process_path_backslash.char', 5, 22, '<IDENT> _win32_process_path_backslash.char'))
        self.assertTrue(has_edge(edges, 5, 22, '<IDENT> _win32_process_path_backslash.char', 5, 8, '<IDENT> _win32_process_path_backslash.result'))
        self.assertTrue(has_edge(edges, 5, 8, '<IDENT> _win32_process_path_backslash.result', 6, 11, '<IDENT> _win32_process_path_backslash.result'))
        self.assertTrue(has_edge(edges, 6, 11, '<IDENT> _win32_process_path_backslash.result', 6, 4, '<RET> _win32_process_path_backslash.return'))

    def test_slicing(self):
        opcode_list.clear()
        source = """

        def _win32_process_path_backslash(value, ix):
            last_char = value[ix - 1:ix]
        """
        self.Infer(source)
        edges = draw_type_inference_graph(opcode_list)
        self.assertTrue(has_edge(edges, 3, 16, '<IDENT> _win32_process_path_backslash.value', 3, 4, '<IDENT> _win32_process_path_backslash.last_char'))

    def test_call_with_named_args(self):
        opcode_list.clear()
        source = """
        import shlex
        s = shlex.shlex(posix=True)
        value = 'some random value'
        splitter = shlex.shlex(value, posix=True)
        """
        self.Infer(source)
        edges = draw_type_inference_graph(opcode_list)
        self.assertTrue(has_edge(edges, 2, 4, '<IDENT> shlex', 2, 4, '<IDENT> shlex.shlex'))
        self.assertTrue(has_edge(edges, 2, 4, '<FUNC> shlex.shlex', 2, 4, '<IDENT> shlex.shlex(posix=True)'))
        self.assertTrue(has_edge(edges, 2, 22, '<ARG> True', 2, 4, '<IDENT> shlex.shlex(posix=True)'))
        self.assertTrue(has_edge(edges, 2, 4, '<IDENT> shlex.shlex(posix=True)', 2, 0, '<IDENT> s'))
        self.assertTrue(has_edge(edges, 4, 11, '<IDENT> shlex.shlex(value, posix=True)', 4, 0, '<IDENT> splitter'))

    def test_attribute_assign(self):
        opcode_list.clear()
        source = """
        import shlex
        s = shlex.shlex(posix=True)
        s.whitespace_split = True
        """
        self.Infer(source)
        edges = draw_type_inference_graph(opcode_list)
        self.assertTrue(has_edge(edges, 3, 21, '<CONST> True', 3, 0, '<IDENT> s.whitespace_split'))

    def test_list_comprehension(self):
        opcode_list.clear()
        source = """
        
        value = 'some random text'
        elements = [expr for expr in value.split(' ')]
        """
        self.Infer(source)
        edges = draw_type_inference_graph(opcode_list)
        self.assertTrue(has_edge(edges, 2, 8, '<CONST> some random text', 2, 0, '<IDENT> value'))
        self.assertTrue(has_edge(edges, 2, 0, '<IDENT> value', 3, 29, '<IDENT> value'))
        self.assertTrue(has_edge(edges, 3, 29, '<IDENT> value', 3, 29, '<IDENT> value.split'))
        self.assertTrue(has_edge(edges, 3, 29, '<FUNC> value.split', 3, 29, '<IDENT> value.split( )'))
        self.assertTrue(has_edge(edges, 3, 41, '<ARG>  ', 3, 29, '<IDENT> value.split( )'))
        self.assertTrue(has_edge(edges, 3, 29, '<IDENT> value.split( )', 3, 21, '<IDENT> <listcomp>.expr'))
        self.assertTrue(has_edge(edges, 3, 21, '<IDENT> <listcomp>.expr', 3, 12, '<IDENT> <listcomp>.expr'))
        self.assertTrue(has_edge(edges, 3, 12, '<IDENT> <listcomp>.expr', 3, 0, '<IDENT> elements'))

    def test_continuous_external_method_call(self):
        opcode_list.clear()
        source = """
        
        def to_bool(value):
            norm = str(value).strip().lower()
        """
        self.Infer(source)
        edges = draw_type_inference_graph(opcode_list)
        self.assertTrue(has_edge(edges, 2, 0, '<TYPE> Noanno', 2, 0, '<PARAM> to_bool.value'))
        self.assertTrue(has_edge(edges, 3, 11, '<FUNC> to_bool.str', 3, 11, '<IDENT> to_bool.str(value)'))
        self.assertTrue(has_edge(edges, 2, 0, '<PARAM> to_bool.value', 3, 15, '<IDENT> to_bool.value'))
        self.assertTrue(has_edge(edges, 3, 15, '<ARG> to_bool.value', 3, 11, '<IDENT> to_bool.str(value)'))
        self.assertTrue(has_edge(edges, 3, 11, '<IDENT> to_bool.str(value)', 3, 11, '<IDENT> to_bool.str(value).strip'))
        self.assertTrue(has_edge(edges, 3, 11, '<FUNC> to_bool.str(value).strip', 3, 11, '<IDENT> to_bool.str(value).strip()'))
        self.assertTrue(has_edge(edges, 3, 11, '<IDENT> to_bool.str(value).strip()', 3, 11, '<IDENT> to_bool.str(value).strip().lower'))
        self.assertTrue(has_edge(edges, 3, 11, '<FUNC> to_bool.str(value).strip().lower', 3, 11, '<IDENT> to_bool.str(value).strip().lower()'))
        self.assertTrue(has_edge(edges, 3, 11, '<IDENT> to_bool.str(value).strip().lower()', 3, 4, '<IDENT> to_bool.norm'))
