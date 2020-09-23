"""
Defines strategies, which sample arguments from Ranges to get command strings to run.
"""


import itertools
from typing import Dict, List

from argsearch import ranges


def apply_substitutions(command: str, substitutions: Dict[str, str]) -> str:
    """
    Given a command string (with templates) and a substitution mapping, produce a
    concrete command string that can be run in a shell.

    Parameters
    ----------
    command
        A string to be executed as a subprocess, with "{arg}" bracketed templates.
    substitutions
        Maps from a bracketed template name to a value to substitute.

    Returns
    -------
    str
        A command string, containing `substitutions` plugged into templates in
        `command`, that can be run in a shell.
    """
    for template, value in substitutions.items():
        command = command.replace("{" + template + "}", value)
    return command


def random(
    templated_string: str, range_map: Dict[str, ranges.Range], trials: int
) -> List[str]:
    """
    Get a list of command strings by random sampling.

    Parameters
    ----------
    templated_string
        A string to be executed as a subprocess, with "{arg}" bracketed templates.
    range_map
        Maps from a template name to a range defining values for that template.
    trials
        How many random trials to run.

    Returns
    -------
    List[str]
        A list of command strings, of length `trials`.
    """

    def random_sample():
        substitutions = {name: rng.random_sample() for name, rng in range_map.items()}
        command_string = apply_substitutions(templated_string, substitutions)
        return command_string

    return [random_sample() for _ in range(trials)]


def grid(
    templated_string: str, range_map: Dict[str, ranges.Range], divisions: int
) -> List[str]:
    """
    Get a list of all command strings to run in a grid search.

    Parameters
    ----------
    templated_string
        A string to be executed as a subprocess, with "{arg}" bracketed templates.
    range_map
        Maps from a template name to a range defining values for that template.
    divisions
        How many slices to divide each numeric range into.

    Returns
    -------
    List[str]
        A list of command strings, for each point on the sampled grid.
    """
    template_names, template_ranges = zip(*range_map.items())
    grids = [rng.grid(divisions) for rng in template_ranges]
    combinations = list(itertools.product(*grids))

    command_strings = []
    for combination in combinations:
        substitutions = dict(zip(template_names, combination))
        command_string = apply_substitutions(templated_string, substitutions)
        command_strings.append(command_string)

    return command_strings


def repeat(command_string: str, repeats: int) -> List[str]:
    """
    Get a list of command strings by repetition.

    Parameters
    ----------
    command_string
        A string to be executed as a subprocess, without any templates.
    repeats
        How many repeats to run.

    Returns
    -------
    List[str]
        `command_string`, repeated `repeats` times.
    """
    return [command_string] * repeats
