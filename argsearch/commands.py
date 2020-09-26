"""
Functions to run user commands.
"""

import json
import multiprocessing
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

from tqdm import tqdm

from argsearch import strategies


def format_header(step: int, command: str, substitutions: Dict[str, str]):
    if substitutions:
        return f"--- [{step}: {substitutions}] {command}"
    return f"--- [{step}] {command}"


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


def stream_command(
    command_template: str, substitutions: Dict[str, str], step: int, monitor: tqdm
) -> None:
    """
    Run a command string, streaming output to stdout.

    Parameters
    ----------
    command_template
        A string to be executed as a subprocess, with "{arg}" bracketed templates.
    substitutions
        A set of substitutions to apply to the command template.
    step
        Which step of the search we're on.
    monitor
        A handle to the parent progress bar.
    """
    command = apply_substitutions(command_template, substitutions)
    monitor.write(format_header(step, command, substitutions))
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, encoding="utf-8",
    )

    assert process.stdout
    for line in process.stdout:
        monitor.write(line, end="")

    process.wait()


def capture_command(
    command_template: str,
    substitutions: Dict[str, str],
    step: int,
    monitor: Optional[tqdm],
) -> Dict[str, Any]:
    """
    Run a command string, capturing and formatting any output.

    Parameters
    ----------
    command_template
        A string to be executed as a subprocess, with "{arg}" bracketed templates.
    substitutions
        A set of substitutions to apply to the command template.
    step
        Which step of the search we're on.
    monitor
        An optional handle to the parent progress bar.

    Returns
    -------
    Dict[str, str]
        The results of evaluating the command with substitution.
    """
    command = apply_substitutions(command_template, substitutions)
    if monitor:
        monitor.set_description(command)
    command_result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        encoding="utf-8",
    )

    return {
        "step": step,
        "command": command,
        "substitutions": substitutions,
        "stdout": command_result.stdout,
        "stderr": command_result.stderr,
        "returncode": command_result.returncode,
    }


def _capture_command_packed(
    args: Tuple[str, Dict[str, str], int, tqdm]
) -> Dict[str, Any]:
    return capture_command(*args)


def run_commands(
    command_template: str,
    substitution_list: List[Dict[str, str]],
    output_json: bool = False,
    num_workers: int = 0,
    disable_bar: bool = False,
) -> None:
    """
    Run a list of command strings, streaming or formatting the output.

    Parameters
    ----------
    command_template
        A string to be executed as a subprocess, with "{arg}" bracketed templates.
    substitution_list
        A list of substitution sets to apply to the command template.
    output_json
        If True, collect output and print at the end, formatted as json.
        Otherwise (default), stream output to stdout as it arrives.
    num_workers
        If provided, use this many worker processes to run commands.
    disable_bar
        If True, disable the progress bar.
    """
    if num_workers > 0:
        process_pool = multiprocessing.Pool(
            num_workers, initializer=tqdm.set_lock, initargs=(tqdm.get_lock(),)
        )

        with tqdm(total=len(substitution_list), disable=disable_bar) as monitor:
            args_packed = [
                (command_template, subs, i, None)
                for i, subs in enumerate(substitution_list)
            ]

            if output_json:
                outputs = []

            try:
                for output in process_pool.imap_unordered(
                    _capture_command_packed, args_packed
                ):
                    monitor.update()

                    if output_json:
                        outputs.append(output)
                    else:
                        header = format_header(
                            output["step"], output["command"], output["substitutions"]
                        )
                        output_with_header = f'{header}\n{output["stdout"]}'
                        monitor.write(output_with_header, end="")
                        if output["stderr"]:
                            sys.stderr.write(output["stderr"])
                            sys.stderr.flush()
            except KeyboardInterrupt:
                pass

            if output_json:
                formatted = json.dumps(outputs)
                monitor.write(formatted)

        return

    with tqdm(substitution_list, disable=disable_bar) as monitor:
        if output_json:
            outputs = []

            try:
                for step, substitutions in enumerate(monitor):
                    outputs.append(
                        capture_command(command_template, substitutions, step, monitor)
                    )
            except KeyboardInterrupt:
                pass

            formatted = json.dumps(outputs)
            monitor.write(formatted)
        else:
            for step, substitutions in enumerate(monitor):
                stream_command(command_template, substitutions, step, monitor)
