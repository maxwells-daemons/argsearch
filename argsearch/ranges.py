"""
Defines Ranges, which specify how to sample arguments of various types.
"""

import abc
import argparse
from typing import List, Union
import numbers
import random

import numpy as np
from scipy import stats


def cast_range_argument(arg: str) -> Union[int, float, str]:
    """
    Determine whether a range argument is integral, floating-point, or categorical.

    Parameters
    ----------
    arg
        The argument to check.

    Returns
    -------
    int
        If `arg` is castable to an integer.
    float
        If `arg` is castable to floating-point, but not an integer.
    string
        If `arg` is not castable to a numeric type.
    """

    try:
        return int(arg)
    except ValueError:
        try:
            return float(arg)
        except ValueError:
            return arg


class Range(abc.ABC):
    """
    A base class for ranges that can be specified for templated arguments.
    """

    @abc.abstractmethod
    def random_sample(self) -> str:
        """
        Get a random sample from this range.

        Returns
        -------
        str
            A value to be substituted into the command in place of a bracketed template.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def grid(self, divisions: int) -> List[str]:
        """
        Get the list of all possible values when divided into `divisions` pieces.

        Parameters
        ----------
        divisions
            How many axis divisions we're using for grid search.

        Returns
        -------
        List[str]
            The list of all values that will be searched over on this range.
        """
        raise NotImplementedError


class IntRange(Range):
    """
    A range of integral values between a minimum and a maximum.
    """

    def __init__(self, a: int, b: int):
        self.min_value = min(a, b)
        self.max_value = max(a, b)

    def random_sample(self) -> str:
        return str(random.randint(self.min_value, self.max_value))

    def grid(self, divisions: int) -> List[str]:
        divisions = min(divisions, self.max_value - self.min_value + 1)
        space = np.linspace(self.min_value, self.max_value, num=divisions, dtype=int)
        return list(map(str, space))


class LogIntRange(Range):
    """
    A log-uniform range of integral values between a minimum and a maximum.
    """

    def __init__(self, a: int, b: int):
        self.min_value = min(a, b)
        self.max_value = max(a, b)
        self.distribution = stats.loguniform(self.min_value, self.max_value)

    def random_sample(self) -> str:
        sample = int(self.distribution.rvs(1).item())
        return str(sample)

    def grid(self, divisions: int) -> List[str]:
        divisions = min(divisions, self.max_value - self.min_value + 1)
        space = np.geomspace(self.min_value, self.max_value, num=divisions, dtype=int)
        return list(map(str, space))


class FloatRange(Range):
    """
    A range of floating-point values between a minimum and a maximum.
    """

    def __init__(self, a: float, b: float):
        self.min_value = min(a, b)
        self.max_value = max(a, b)

    def random_sample(self) -> str:
        return str(random.uniform(self.min_value, self.max_value))

    def grid(self, divisions: int) -> List[str]:
        space = np.linspace(self.min_value, self.max_value, num=divisions, dtype=float)
        return list(map(str, space))


class LogFloatRange(Range):
    """
    A log-uniform range of floating-point values between a minimum and a maxmimum.
    """

    def __init__(self, a: float, b: float):
        self.min_value = min(a, b)
        self.max_value = max(a, b)
        self.distribution = stats.loguniform(self.min_value, self.max_value)

    def random_sample(self) -> str:
        return str(self.distribution.rvs(1).item())

    def grid(self, divisions: int) -> List[str]:
        space = np.geomspace(self.min_value, self.max_value, num=divisions, dtype=float)
        return list(map(str, space))


class CategoricalRange(Range):
    """
    A range containing a fixed set of categories.

    NOTE: this is not divided during grid search; every category will be searched over.
    If this behavior is not desirable, consider a random search.
    """

    def __init__(self, categories: List[str]):
        self.categories = categories

    def random_sample(self) -> str:
        return random.choice(self.categories)

    def grid(self, divisions: int) -> List[str]:
        return self.categories


class TemplateRange(argparse.Action):
    """
    An argparse Action to parse a template range argument into a Range object.
    """

    def __call__(self, parser, namespace, values, option_string):
        if len(values) < 2:
            raise argparse.ArgumentTypeError(
                "A template range requires 2 or more values."
            )

        if len(values) == 2:
            first = cast_range_argument(values[0])
            second = cast_range_argument(values[1])

            if isinstance(first, int) and isinstance(second, int):
                setattr(namespace, self.dest, IntRange(first, second))
                return

            if isinstance(first, numbers.Number) and isinstance(second, numbers.Number):
                setattr(namespace, self.dest, FloatRange(first, second))
                return

        if len(values) == 3 and values[0] == "LOG":
            first = cast_range_argument(values[1])
            second = cast_range_argument(values[2])

            if isinstance(first, int) and isinstance(second, int):
                setattr(namespace, self.dest, LogIntRange(first, second))
                return

            if isinstance(first, numbers.Number) and isinstance(second, numbers.Number):
                setattr(namespace, self.dest, LogFloatRange(first, second))
                return

        setattr(namespace, self.dest, CategoricalRange(values))
