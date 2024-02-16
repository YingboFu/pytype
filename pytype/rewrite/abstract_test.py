from typing import Tuple

from pytype.rewrite import abstract
from pytype.rewrite.flow import variables
from typing_extensions import assert_type

import unittest


class PythonConstantTest(unittest.TestCase):

  def test_equal(self):
    c1 = abstract.PythonConstant('a')
    c2 = abstract.PythonConstant('a')
    self.assertEqual(c1, c2)

  def test_not_equal(self):
    c1 = abstract.PythonConstant('a')
    c2 = abstract.PythonConstant('b')
    self.assertNotEqual(c1, c2)

  def test_constant_type(self):
    c = abstract.PythonConstant('a')
    assert_type(c.constant, str)

  def test_get_type_from_variable(self):
    var = variables.Variable.from_value(abstract.PythonConstant(True))
    const = var.get_atomic_value(abstract.PythonConstant[int]).constant
    assert_type(const, int)


class GetAtomicConstantTest(unittest.TestCase):

  def test_get(self):
    var = variables.Variable.from_value(abstract.PythonConstant('a'))
    const = abstract.get_atomic_constant(var)
    self.assertEqual(const, 'a')

  def test_get_with_type(self):
    var = variables.Variable.from_value(abstract.PythonConstant('a'))
    const = abstract.get_atomic_constant(var, str)
    assert_type(const, str)
    self.assertEqual(const, 'a')

  def test_get_with_bad_type(self):
    var = variables.Variable.from_value(abstract.PythonConstant('a'))
    with self.assertRaisesRegex(ValueError, 'expected int, got str'):
      abstract.get_atomic_constant(var, int)

  def test_get_with_parameterized_type(self):
    var = variables.Variable.from_value(abstract.PythonConstant(('a',)))
    const = abstract.get_atomic_constant(var, Tuple[str, ...])
    assert_type(const, Tuple[str, ...])
    self.assertEqual(const, ('a',))

  def test_get_with_bad_parameterized_type(self):
    var = variables.Variable.from_value(abstract.PythonConstant('a'))
    with self.assertRaisesRegex(ValueError, 'expected tuple, got str'):
      abstract.get_atomic_constant(var, Tuple[str, ...])


if __name__ == '__main__':
  unittest.main()
