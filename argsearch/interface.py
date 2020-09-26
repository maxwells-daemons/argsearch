"""
Contains the main interface, used to parse arguments and run the program.
"""

import argparse
import os
import re
from typing import Dict, List, Set

from argsearch import commands, optimization, ranges, strategies


def positive_int(arg: str) -> int:
    value = int(arg)
    if value < 1:
        raise argparse.ArgumentTypeError("Value must be a positive integer.")
    return value


def parse_range_args(
    range_args: List[str], templates: Set[str]
) -> Dict[str, ranges.Range]:
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
        usage += f" --{template} ([LOG] low high | A B C [D ...])"

    range_parser = argparse.ArgumentParser(
        "ranges",
        description="One range specifier per template in the input command. "
        "If two numbers (int or float) are provided, they are treated as the min and "
        "max of a numeric range. Otherwise, they are treated as separate categories."
        "If LOG and two numbers are present, they define a log-uniform range.",
        add_help=True,
        usage=usage,
        allow_abbrev=False,
    )
    range_group = range_parser.add_argument_group("templates specified")

    try:
        for template in templates:
            range_group.add_argument(
                f"--{template}", action=ranges.TemplateRange, nargs="*", required=True,
            )
        parsed_ranges = range_parser.parse_args(range_args)
    except SystemExit:
        os._exit(2)

    return vars(parsed_ranges)


def get_template_names(command_string: str) -> Set[str]:
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
    names = {template.strip("{}") for template in templates}
    return names


def main():
    base_parser = argparse.ArgumentParser(
        description="Run the same command multiple times with different values for its "
        "arguments.",
    )
    base_parser.add_argument(
        "--num-workers",
        type=positive_int,
        default=0,
        metavar="N",
        help="if provided, split work among N worker processes",
    )
    base_parser.add_argument(
        "--output-json",
        action="store_true",
        help="capture output and format it as JSON instead of streaming to terminal",
    )

    base_parser.add_argument(
        "--disable-bar", action="store_true", help="disable the progress bar"
    )

    strategy_parsers = base_parser.add_subparsers(
        title="strategy", description="the search strategy to use", dest="strategy",
    )
    # Workaround for older Python versions; see
    # https://stackoverflow.com/questions/23349349/argparse-with-required-subparser
    strategy_parsers.required = True

    random_parser = strategy_parsers.add_parser("random", help="random search")
    random_parser.add_argument(
        "trials", type=positive_int, help="number of random trials to run"
    )
    random_parser.set_defaults(strategy="random")

    quasirandom_parser = strategy_parsers.add_parser(
        "quasirandom", help="low-discrepancy quasirandom search"
    )
    quasirandom_parser.add_argument(
        "trials", type=positive_int, help="number of quasirandom trials to run"
    )
    quasirandom_parser.set_defaults(strategy="quasirandom")

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
    repeat_parser.add_argument("command", help="the command to run")

    minimize_parser = strategy_parsers.add_parser(
        "minimize", help="minimize with Bayesian optimization"
    )
    minimize_parser.add_argument(
        "trials", type=positive_int, help="number of trials to make"
    )
    minimize_parser.set_defaults(strategy="minimize")

    maximize_parser = strategy_parsers.add_parser(
        "maximize", help="maximize with Bayesian optimization"
    )
    maximize_parser.add_argument(
        "trials", type=positive_int, help="number of trials to make"
    )
    maximize_parser.set_defaults(strategy="maximize")

    for subparser in [
        random_parser,
        quasirandom_parser,
        grid_parser,
        minimize_parser,
        maximize_parser,
    ]:
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
        parsed_ranges = parse_range_args(base_args.ranges, templates)

    if base_args.strategy == "minimize":
        optimization.optimize_command(
            command_template=base_args.command,
            range_map=parsed_ranges,
            trials=base_args.trials,
            maximize=False,
            output_json=base_args.output_json,
            num_workers=base_args.num_workers,
            disable_bar=base_args.disable_bar,
        )
        return

    if base_args.strategy == "maximize":
        optimization.optimize_command(
            command_template=base_args.command,
            range_map=parsed_ranges,
            trials=base_args.trials,
            maximize=True,
            output_json=base_args.output_json,
            num_workers=base_args.num_workers,
            disable_bar=base_args.disable_bar,
        )
        return

    if base_args.strategy == "random":
        substitutions = strategies.random(parsed_ranges, base_args.trials)
    elif base_args.strategy == "quasirandom":
        substitutions = strategies.sobol(parsed_ranges, base_args.trials)
    elif base_args.strategy == "grid":
        substitutions = strategies.grid(parsed_ranges, base_args.divisions)
    elif base_args.strategy == "repeat":
        substitutions = [{}] * base_args.repeats
    else:
        raise ValueError(f"Unrecognized strategy: {base_args.strategy}.")

    commands.run_commands(
        base_args.command,
        substitutions,
        base_args.output_json,
        base_args.num_workers,
        base_args.disable_bar,
    )
