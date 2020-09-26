"""
Defines strategies, which sample arguments from Ranges to get command strings to run.
"""


import collections
import itertools
from typing import Dict, List

import numpy as np
import sobol_seq

from argsearch import ranges


def random(range_map: Dict[str, ranges.Range], trials: int) -> List[Dict[str, str]]:
    """
    Get a list of substitutions by random sampling.

    Parameters
    ----------
    range_map
        Maps from a template name to a range defining values for that template.
    trials
        How many random trials to run.

    Returns
    -------
    List[Dict[str, str]]
        A list of argument substitutions, of length `trials`.
    """

    def random_sample():
        return {name: rng.random_sample() for name, rng in range_map.items()}

    return [random_sample() for _ in range(trials)]


def sobol(range_map: Dict[str, ranges.Range], trials: int) -> List[Dict[str, str]]:
    """
    Get a list of substitutions by quasirandom sampling from a Sobol sequence.

    Parameters
    ----------
    range_map
        Maps from a template name to a range defining values for that template.
    trials
        How many random trials to run.

    Returns
    -------
    List[Dict[str, str]]
        A list of argument substitutions, of length `trials`.
    """
    ordered_range_map = collections.OrderedDict(range_map)
    sobol_values = sobol_seq.i4_sobol_generate(len(range_map), trials)

    def transform_vector(uniform_vector):
        substitution = {}
        for uniform_sample, (name, rng) in zip(
            uniform_vector, ordered_range_map.items()
        ):
            substitution[name] = rng.transform_uniform_sample(uniform_sample)
        return substitution

    return [transform_vector(vector) for vector in sobol_values]


def grid(range_map: Dict[str, ranges.Range], divisions: int) -> List[Dict[str, str]]:
    """
    Get a list of all substitutions to run in a grid search.

    Parameters
    ----------
    range_map
        Maps from a template name to a range defining values for that template.
    divisions
        How many slices to divide each numeric range into.

    Returns
    -------
    List[Dict[str, str]]
        A list of substitutions, for each point on the sampled grid.
    """
    template_names, template_ranges = zip(*range_map.items())
    grids = [rng.grid(divisions) for rng in template_ranges]
    combinations = list(itertools.product(*grids))
    return [dict(zip(template_names, combination)) for combination in combinations]
