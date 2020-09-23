"""
Functions to run user commands.
"""

import subprocess
from typing import Any, Dict, List, Set

from tqdm import tqdm


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
    monitor.write(f"--- [{step}] {command}")
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, encoding="utf-8",
    )

    assert process.stdout
    for line in process.stdout:
        monitor.write(line, end="")

    process.wait()


def capture_command(command: str, step: int, monitor: tqdm) -> Dict[str, Any]:
    """
    Run a command string, capturing and formatting any output.

    Parameters
    ----------
    command
        The command string to run. Tokenized with the shell defaults.
    step
        Which step of the search we're on.
    monitor
        A handle to the parent progress bar.

    Returns
    -------
    Dict[str, str]
        The results of evaluating the command with substitution.
    """
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
