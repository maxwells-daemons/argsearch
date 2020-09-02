# argsearch
`argsearch` is a simple and composable tool for running the same command many times with different combinations of arguments.
It aims to make random search and grid search easy for things like hyperparameter tuning and setting simulation parameters, while only requiring that your program accepts command line arguments in some form.

## Example
```
$ argsearch grid 3 'echo {a} {b}' --a 0.0 1.5 --b X Y
[
{"args": {"a": "0.0", "b": "X"}, "command": "echo 0.0 X", "stdout": "0.0 X\n", "stderr": "", "returncode": 0},
{"args": {"a": "0.0", "b": "Y"}, "command": "echo 0.0 Y", "stdout": "0.0 Y\n", "stderr": "", "returncode": 0},
{"args": {"a": "0.75", "b": "X"}, "command": "echo 0.75 X", "stdout": "0.75 X\n", "stderr": "", "returncode": 0},
{"args": {"a": "0.75", "b": "Y"}, "command": "echo 0.75 Y", "stdout": "0.75 Y\n", "stderr": "", "returncode": 0},
{"args": {"a": "1.5", "b": "X"}, "command": "echo 1.5 X", "stdout": "1.5 X\n", "stderr": "", "returncode": 0},
{"args": {"a": "1.5", "b": "Y"}, "command": "echo 1.5 Y", "stdout": "1.5 Y\n", "stderr": "", "returncode": 0}
]
```

## Installation

```
pip install argsearch
```

## Usage

`argsearch` takes 3 kinds of arguments:
 - A **search strategy** (*random,* *grid,* or *repeat*) and its configuration:
    - For *random*: **trials**, the number of random trials to run.
    - For *grid*: **divisions**, the number of points to try in each numeric range.
    - For *repeat*: **repeats**, the number of times to repeat the command.
 - A **command string** with **templates** designated by bracketed names (e.g. `'python my_script.py --flag {value}'`.
 -  A **range** for each template in the command string (e.g. `--value 1 100`).

Then, `argsearch` runs the command string several times, each time replacing the templates with values from their associated ranges.
Note that the *repeat* strategy does not admit templates or range arguments.

### Search Strategies

Three search strategies are currently implemented:
 - **Random search** samples uniformly randomly from specified ranges for a fixed number
     of trials.
 - **Grid search** divides each numeric range into a fixed number of
     evenly-spaced points and runs once for each possible combination of
     inputs.
 - **Repeat** runs the same command a fixed number of times.

### Ranges
Three types of ranges are available:
 - **Floating-point ranges** are specified by a minimum and maximum floating-point value (e.g. `--value 0.0 1.0`).
 - **Integer ranges** are specified by a minimum and maximum integer (e.g. `--value 1 100`). Integer ranges are guaranteed to only yield integer values.
 - **Categorical ranges** are specified by a list of non-numeric categories, or more than two numbers (e.g. `--value A B C`, `--value 2 4 8 16`). Categorical ranges only draw values from the listed categories, and are not divided up during a grid search.

### Output

The output is JSON, which can be wrangled with [jq](https://github.com/stedolan/jq) or other tools, or dumped to a file. The run is a list of mappings, one per command call, each of which has the following keys:
 - `args`: a mapping of argument names to values.
 - `command`: the command string with substitutions applied.
 - `stdout`: a string containing the command's stdout.
 - `stderr`: a string containing the command's stderr.
 - `returncode`: an integer return code for the command.
