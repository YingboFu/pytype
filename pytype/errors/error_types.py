"""Types for structured errors."""

import dataclasses

from typing import Any, Sequence, Tuple, Optional

from pytype.types import types


class ReturnValueMixin:
  """Mixin for exceptions that hold a return node and variable."""

  def __init__(self):
    super().__init__()
    self.return_node = None
    self.return_variable = None

  def set_return(self, node, var):
    self.return_node = node
    self.return_variable = var

  def get_return(self, state):
    return state.change_cfg_node(self.return_node), self.return_variable


@dataclasses.dataclass(eq=True, frozen=True)
class BadType:
  name: Optional[str]
  typ: types.BaseValue
  # Should be matcher.ErrorDetails but can't use due to circular dep.
  error_details: Optional[Any] = None


# These names are chosen to match pytype error classes.
# pylint: disable=g-bad-exception-name
class FailedFunctionCall(Exception, ReturnValueMixin):
  """Exception for failed function calls."""

  def __init__(self):
    super().__init__()
    self.name = "<no name>"

  def __gt__(self, other):
    return other is None

  def __le__(self, other):
    return not self.__gt__(other)


class NotCallable(FailedFunctionCall):
  """For objects that don't have __call__."""

  def __init__(self, obj):
    super().__init__()
    self.obj = obj


class UndefinedParameterError(FailedFunctionCall):
  """Function called with an undefined variable."""

  def __init__(self, name):
    super().__init__()
    self.name = name


class DictKeyMissing(Exception, ReturnValueMixin):
  """When retrieving a key that does not exist in a dict."""

  def __init__(self, name):
    super().__init__()
    self.name = name

  def __gt__(self, other):
    return other is None

  def __le__(self, other):
    return not self.__gt__(other)


@dataclasses.dataclass(eq=True, frozen=True)
class BadCall:
  sig: types.Signature
  passed_args: Sequence[Tuple[str, types.BaseValue]]
  bad_param: Optional[BadType]


class InvalidParameters(FailedFunctionCall):
  """Exception for functions called with an incorrect parameter combination."""

  def __init__(self, sig, passed_args, ctx, bad_param=None):
    super().__init__()
    self.name = sig.name
    passed_args = [(name, ctx.convert.merge_values(arg.data))
                   for name, arg, _ in sig.iter_args(passed_args)]
    self.bad_call = BadCall(sig=sig, passed_args=passed_args,
                            bad_param=bad_param)


class WrongArgTypes(InvalidParameters):
  """For functions that were called with the wrong types."""

  def __init__(self, sig, passed_args, ctx, bad_param):
    if not sig.has_param(bad_param.name):
      sig = sig.insert_varargs_and_kwargs(
          name for name, *_ in sig.iter_args(passed_args))
    super().__init__(sig, passed_args, ctx, bad_param)

  def __gt__(self, other):
    if other is None:
      return True
    if not isinstance(other, WrongArgTypes):
      # WrongArgTypes should take precedence over other FailedFunctionCall
      # subclasses but not over unrelated errors like DictKeyMissing.
      return isinstance(other, FailedFunctionCall)
    # The signature that has fewer *args/**kwargs tends to be more precise.
    def starcount(err):
      return (bool(err.bad_call.sig.varargs_name) +
              bool(err.bad_call.sig.kwargs_name))
    return starcount(self) < starcount(other)

  def __le__(self, other):
    return not self.__gt__(other)


class WrongArgCount(InvalidParameters):
  """E.g. if a function expecting 4 parameters is called with 3."""


class WrongKeywordArgs(InvalidParameters):
  """E.g. an arg "x" is passed to a function that doesn't have an "x" param."""

  def __init__(self, sig, passed_args, ctx, extra_keywords):
    super().__init__(sig, passed_args, ctx)
    self.extra_keywords = tuple(extra_keywords)


class DuplicateKeyword(InvalidParameters):
  """E.g. an arg "x" is passed to a function as both a posarg and a kwarg."""

  def __init__(self, sig, passed_args, ctx, duplicate):
    super().__init__(sig, passed_args, ctx)
    self.duplicate = duplicate


class MissingParameter(InvalidParameters):
  """E.g. a function requires parameter 'x' but 'x' isn't passed."""

  def __init__(self, sig, passed_args, ctx, missing_parameter):
    super().__init__(sig, passed_args, ctx)
    self.missing_parameter = missing_parameter
# pylint: enable=g-bad-exception-name
