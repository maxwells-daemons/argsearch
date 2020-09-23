"""
Functions to run user commands.
"""

import json
import multiprocessing
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

from tqdm import tqdm


def format_header(step: int, command: str):
    return f"--- [{step}] {command}"


def stream_command(command: str, step: int, monitor: tqdm) -> None:
    """
    Run a command string, streaming output to the stdout.

    Parameters
    ----------
    command
        The command string to run. Tokenized with the shell defaults.
    step
        Which step of the search we're on.
    monitor
        A handle to the parent progress bar.
    """
    monitor.write(format_header(step, command))
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, encoding="utf-8",
    )

    assert process.stdout
    for line in process.stdout:
        monitor.write(line, end="")

    process.wait()


def capture_command(command: str, step: int, monitor: Optional[tqdm]) -> Dict[str, Any]:
    """
    Run a command string, capturing and formatting any output.

    Parameters
    ----------
    command
        The command string to run. Tokenized with the shell defaults.
    step
        Which step of the search we're on.
    monitor
        An optional handle to the parent progress bar.

    Returns
    -------
    Dict[str, str]
        The results of evaluating the command with substitution.
    """
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
        "stdout": command_result.stdout,
        "stderr": command_result.stderr,
        "returncode": command_result.returncode,
    }


def _capture_command_packed(args: Tuple[str, int, tqdm]) -> Dict[str, Any]:
    return capture_command(*args)


def run_commands(
    command_strings: List[str],
    output_json: bool = False,
    num_workers: int = 0,
    disable_bar: bool = False,
) -> None:
    """
    Run a list of command strings, streaming or formatting the output.

    Parameters
    ----------
    command_strings
        All command strings to run.
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

        with tqdm(total=len(command_strings), disable=disable_bar) as monitor:
            args_packed = [(comm, i, None) for i, comm in enumerate(command_strings)]

            if output_json:
                outputs = []

            for output in process_pool.imap_unordered(
                _capture_command_packed, args_packed
            ):
                monitor.update()

                if output_json:
                    outputs.append(output)
                else:
                    header = format_header(output["step"], output["command"])
                    output_with_header = f'{header}\n{output["stdout"]}'
                    monitor.write(output_with_header, end="")
                    if output["stderr"]:
                        sys.stderr.write(output["stderr"])
                        sys.stderr.flush()

            if output_json:
                formatted = json.dumps(outputs)
                monitor.write(formatted)

        return

    with tqdm(command_strings, disable=disable_bar) as monitor:
        if output_json:
            outputs = [
                capture_command(command, step, monitor)
                for step, command in enumerate(monitor)
            ]
            formatted = json.dumps(outputs)
            monitor.write(formatted)
        else:
            for step, command in enumerate(monitor):
                stream_command(command, step, monitor)
