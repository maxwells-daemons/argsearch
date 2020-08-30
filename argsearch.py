"""
A command-line utility to run the same command many times with different values for
its arguments.
"""

import abc
import argparse
import itertools
import json
import os
import random
import re
import subprocess
from typing import Any, Dict, List

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
                "a template range requires 2 or more values"
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


def positive_int(arg: str) -> int:
    value = int(arg)
    if value < 1:
        raise argparse.ArgumentTypeError("N must be a positive integer")
    return value


def run_templated_command(command: str, args: Dict[str, str]) -> Dict[str, Any]:
    """
    Run a command with bracketed templates, substituting in appropriate arguments.

    Parameters
    ----------
    command
        A string to be executed as a subprocess, with "{arg}" bracketed templates.
    args
        Maps from a bracketed template name to a value to substitute.

    Returns
    -------
    Dict[str, str]
        The results of evaluating the command with substitution.
    """
    for template, value in args.items():
        command = command.replace("{" + template + "}", value)
    command_result = subprocess.run(
        command, capture_output=True, shell=True, encoding="utf-8"
    )

    return {
        "args": args,
        "command": command,
        "stdout": command_result.stdout,
        "stderr": command_result.stderr,
        "returncode": command_result.returncode,
    }


def main():
    base_parser = argparse.ArgumentParser(
        description="Run the same command multiple times with different values for its "
        'arguments. For example, `argsearch "echo {a}" random 10 --a 1 100`.',
    )
    base_parser.add_argument(
        "command", help="the command to run, including at least one bracketed template"
    )
    base_parser.add_argument(
        "strategy", choices=["random", "grid"], help="the search strategy to use"
    )
    base_parser.add_argument(
        "N",
        type=positive_int,
        help="in a random search, the number of trials to run; in a grid search, the "
        "number of divisions for each numeric range",
    )
    base_parser.add_argument(
        "template_ranges",
        nargs=argparse.REMAINDER,
        help="a numeric or categorical range for each template in the command",
    )
    base_args = base_parser.parse_args()

    templates = re.findall("\{.+?\}", base_args.command)
    if not templates:
        raise ValueError("At least one argument template must be provided.")

    template_range_parser = argparse.ArgumentParser(
        "template_ranges",
        description="One range specifier per template in the input command. "
        "If two numbers (int or float) are provided, they are treated as the min and "
        "max of a numeric range. Otherwise, they are treated as separate categories.",
        add_help=True,
        usage="... --arg min max | --arg A B C [D ...]",
        allow_abbrev=False,
    )
    range_group = template_range_parser.add_argument_group("templates specified")

    try:
        for template in templates:
            range_group.add_argument(
                f"--{template.strip('{}')}",
                action=TemplateRange,
                nargs="*",
                required=True,
            )
        range_args = template_range_parser.parse_args(base_args.template_ranges)
    except SystemExit:
        os._exit(2)

    print("[")
    if base_args.strategy == "random":
        for i in range(base_args.N):
            args = {k: v.random_sample() for k, v in vars(range_args).items()}
            result = run_templated_command(base_args.command, args)
            suffix = ",\n" if i < base_args.N - 1 else "\n"
            print(json.dumps(result), end=suffix)
    else:
        arg_names, ranges = zip(*vars(range_args).items())
        grids = [r.grid(base_args.N) for r in ranges]
        combinations = list(itertools.product(*grids))
        for i, arg_values in enumerate(combinations):
            args = dict(zip(arg_names, arg_values))
            result = run_templated_command(base_args.command, args)
            suffix = ",\n" if i < len(combinations) - 1 else "\n"
            print(json.dumps(result), end=suffix)
    print("]")


if __name__ == "__main__":
    main()
