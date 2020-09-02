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


def positive_int(arg: str) -> int:
    value = int(arg)
    if value < 1:
        raise argparse.ArgumentTypeError("Value must be a positive integer.")
    return value


def get_template_names(command_string: str) -> List[str]:
    """
    Get the names of all of the bracketed templates in a command string.

    Parameters
    ----------
    command_string
        The string to read templates from.

    Returns
    -------
    List[str]
        A list of the templates in the command string, without brackets.
    """
    templates = re.findall("\{.+?\}", command_string)
    names = [template.strip("{}") for template in templates]
    return names


def run_command(command: str) -> Dict[str, Any]:
    """
    Run a command without templates, capturing and formatting any output.

    Parameters
    ----------
    command
        The command string to run. Tokenized with the shell defaults.

    Returns
    -------
    Dict[str, str]
        The results of evaluating the command with substitution.
    """
    command_result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        encoding="utf-8",
    )

    return {
        "command": command,
        "stdout": command_result.stdout,
        "stderr": command_result.stderr,
        "returncode": command_result.returncode,
    }


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

    results = run_command(command)
    return {"args": args, **results}


def parse_range_args(range_args: List[str], templates: List[str]) -> Dict[str, Range]:
    """
    Parse the provided range arguments into Range objects.

    Parameters
    ----------
    range_args
        A list of range arguments provided on the command line.
    templates
        A list of template names to be filled in the command string.

    Returns
    -------
    Dict[str, Range]
        A mapping from template names to their specified ranges.
    """
    usage = "..."
    for template in templates:
        usage += f" --{template} (low high | A B C [D ...])"

    range_parser = argparse.ArgumentParser(
        "ranges",
        description="One range specifier per template in the input command. "
        "If two numbers (int or float) are provided, they are treated as the min and "
        "max of a numeric range. Otherwise, they are treated as separate categories.",
        add_help=True,
        usage=usage,
        allow_abbrev=False,
    )
    range_group = range_parser.add_argument_group("templates specified")

    try:
        for template in templates:
            range_group.add_argument(
                f"--{template}", action=TemplateRange, nargs="*", required=True,
            )
        ranges = range_parser.parse_args(range_args)
    except SystemExit:
        os._exit(2)

    return vars(ranges)


def main():
    base_parser = argparse.ArgumentParser(
        description="Run the same command multiple times with different values for its "
        "arguments.",
    )

    strategy_parsers = base_parser.add_subparsers(
        title="strategy", description="the search strategy to use"
    )

    random_parser = strategy_parsers.add_parser("random", help="random search")
    random_parser.add_argument(
        "trials", type=positive_int, help="number of random trials to run"
    )
    random_parser.set_defaults(strategy="random")

    grid_parser = strategy_parsers.add_parser("grid", help="grid search")
    grid_parser.add_argument(
        "divisions",
        type=positive_int,
        help="number of ways to divide each numeric interval",
    )
    grid_parser.set_defaults(strategy="grid")

    repeat_parser = strategy_parsers.add_parser("repeat", help="repeat a command")
    repeat_parser.add_argument(
        "repeats", type=positive_int, help="number of repeats to run"
    )
    repeat_parser.set_defaults(strategy="repeat")
    repeat_parser.add_argument(
        "command", help="the command to run",
    )

    for subparser in [random_parser, grid_parser]:
        subparser.add_argument(
            "command",
            help="the command to run, including at least one bracketed template",
        )
        subparser.add_argument(
            "ranges",
            nargs=argparse.REMAINDER,
            help="a numeric or categorical range for each template in the command",
        )

    base_args = base_parser.parse_args()
    templates = get_template_names(base_args.command)

    if base_args.strategy != "repeat":
        if not templates:
            raise ValueError(
                "At least one template must be provided with the "
                f"'{base_args.strategy}' strategy."
            )

        ranges = parse_range_args(base_args.ranges, templates)

    print(base_args.strategy)

    print("[")
    if base_args.strategy == "random":
        for i in range(base_args.trials):
            args = {k: v.random_sample() for k, v in ranges.items()}
            result = run_templated_command(base_args.command, args)
            suffix = ",\n" if i < base_args.trials - 1 else "\n"
            print(json.dumps(result), end=suffix)
    elif base_args.strategy == "grid":
        arg_names, ranges = zip(*ranges.items())
        grids = [r.grid(base_args.divisions) for r in ranges]
        combinations = list(itertools.product(*grids))

        for i, arg_values in enumerate(combinations):
            args = dict(zip(arg_names, arg_values))
            result = run_templated_command(base_args.command, args)
            suffix = ",\n" if i < len(combinations) - 1 else "\n"
            print(json.dumps(result), end=suffix)
    elif base_args.strategy == "repeat":
        for i in range(base_args.repeats):
            result = run_command(base_args.command)
            suffix = ",\n" if i < base_args.repeats - 1 else "\n"
            print(json.dumps(result), end=suffix)
    else:
        assert False
    print("]")


if __name__ == "__main__":
    main()
