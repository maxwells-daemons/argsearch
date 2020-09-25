"""
Code relating to sequential optimization.
"""

import json
import multiprocessing
import sys
from typing import Dict
import warnings

import skopt
from tqdm import tqdm

from argsearch import commands, ranges, strategies

# See: https://github.com/scikit-optimize/scikit-optimize/issues/302
warnings.filterwarnings(
    "ignore", message="The objective has been evaluated at this point before."
)


def get_command_output(output: str) -> float:
    lines = output.strip().split("\n")
    return float(lines[-1])


def optimize_command(
    command_template: str,
    range_map: Dict[str, ranges.Range],
    trials: int,
    maximize: bool,
    output_json: bool = False,
    num_workers: int = 0,
    disable_bar: bool = False,
) -> None:
    """
    Optimize a command with closed-loop Bayesian optimization.
    """

    if num_workers == 0:
        num_workers = 1

    process_pool = multiprocessing.Pool(
        num_workers, initializer=tqdm.set_lock, initargs=(tqdm.get_lock(),)
    )

    template_names = list(range_map.keys())
    skopt_spaces = [range_map[name].to_skopt() for name in template_names]
    optimizer = skopt.Optimizer(skopt_spaces, n_jobs=-1)

    def eval_commands(args_list, step):
        packed_command_args = []
        for i, args in enumerate(args_list):
            substitutions = dict(zip(template_names, map(str, args)))
            command_string = strategies.apply_substitutions(
                command_template, substitutions
            )
            packed_command_args.append((command_string, step + i, None))

        return process_pool.imap_unordered(
            commands._capture_command_packed, packed_command_args
        )

    best_objective = None
    steps_since_improvement = 0

    with tqdm(total=trials, disable=disable_bar) as monitor:
        if output_json:
            outputs = []

        for step in range(0, trials, num_workers):
            args_list = optimizer.ask(num_workers)
            objective_values = []

            for output in eval_commands(args_list, step):
                try:
                    objective = get_command_output(output["stdout"])
                except ValueError:
                    raise ValueError(
                        "Command's last line of output must be a single number."
                    )

                if maximize:
                    objective *= -1
                objective_values.append(objective)

                if output_json:
                    outputs.append(output)
                else:
                    header = commands.format_header(output["step"], output["command"])
                    output_with_header = f'{header}\n{output["stdout"]}'
                    monitor.write(output_with_header, end="")
                    if output["stderr"]:
                        sys.stderr.write(output["stderr"])
                        sys.stderr.flush()

                if best_objective is None or best_objective > min(objective_values):
                    best_objective = min(objective_values)
                    steps_since_improvement = 0
                else:
                    steps_since_improvement += 1

                monitor.set_postfix(
                    {
                        "Current best": str(best_objective),
                        "Steps since improvement": str(steps_since_improvement),
                    }
                )
                monitor.update()

            optimizer.tell(args_list, objective_values)

        if output_json:
            formatted = json.dumps(outputs)
            monitor.write(formatted)
