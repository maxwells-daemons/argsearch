"""
Defines Ranges, which specify how to sample arguments of various types.
"""

import abc
import argparse
from typing import List
import random

import numpy as np


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

    def __init__(self, min_value: int, max_value: int):
        self.min_value = min_value
        self.max_value = max_value

    def random_sample(self) -> str:
        return str(random.randint(self.min_value, self.max_value))

    def grid(self, divisions: int) -> List[str]:
        divisions = min(divisions, self.max_value - self.min_value + 1)
        space = np.linspace(self.min_value, self.max_value, num=divisions, dtype=int)
        return list(map(str, space))


class FloatRange(Range):
    """
    A range of floating-point values between a minimum and a maximum.
    """

    def __init__(self, min_value: float, max_value: float):
        self.min_value = min_value
        self.max_value = max_value

    def random_sample(self) -> str:
        return str(random.uniform(self.min_value, self.max_value))

    def grid(self, divisions: int) -> List[str]:
        space = np.linspace(self.min_value, self.max_value, num=divisions, dtype=float)
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
            try:
                value_1 = int(values[0])
                value_2 = int(values[1])
                min_value = min(value_1, value_2)
                max_value = max(value_1, value_2)
                setattr(namespace, self.dest, IntRange(min_value, max_value))
                return
            except ValueError:
                pass

            try:
                value_1 = float(values[0])
                value_2 = float(values[1])
                min_value = min(value_1, value_2)
                max_value = max(value_1, value_2)
                setattr(namespace, self.dest, FloatRange(min_value, max_value))
                return
            except ValueError:
                pass

        setattr(namespace, self.dest, CategoricalRange(values))
