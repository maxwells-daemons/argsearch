# argsearch
`argsearch` is a simple and composable tool for running the same command many times with different combinations of arguments.
It aims to easily automate tasks like hyperparameter tuning and setting simulation parameters, while only requiring that your program accepts command-line arguments in some form.

Key features include:
 - Easy integration with any program that takes command-line arguments.
 - Support for searching over integer, floating-point, and categorical arguments with several search strategies.
 - The ability to produce JSON-structured output, making it composable with other command-line tools like [`jq`](https://stedolan.github.io/jq/).
 - Multiprocessing, enabling running many experiments in parallel.
 
![MIT license badge](https://img.shields.io/github/license/maxwells-daemons/argsearch)
![Python version badge](https://img.shields.io/pypi/pyversions/argsearch)

## Examples
### Basic usage
```
$ argsearch grid 3 "echo {a} {b}" --a 1 10 --b X Y
--- [0] echo 1 X                                                                                                     
1 X                                                                                                                  
--- [1] echo 5 X                                                                                                     
5 X                                                                                                                  
--- [2] echo 10 X                                                                                                    
10 X                                                                                                                 
--- [3] echo 1 Y                                                                                                     
1 Y                                                                                                                  
--- [4] echo 5 Y                                                                                                     
5 Y                                                                                                                  
--- [5] echo 10 Y                                                                                                    
10 Y                                                                                                                   
100%|██████████████████████████████| 6/6 [00:00<00:00, 220.49it/s]
```
### Composing pipelines with `argsearch` and `jq`
```
$ argsearch --output-json repeat 2 "echo hello" | jq
[
  {
    "step": 0,
    "command": "echo hello",
    "stdout": "hello\n",
    "stderr": "",
    "returncode": 0
  },
  {
    "step": 1,
    "command": "echo hello",
    "stdout": "hello\n",
    "stderr": "",
    "returncode": 0
  }
]
```

```
$ argsearch --output-json random 100 "echo {x}" --x 0.0 1.0 | jq -j '.[] | .stdout' | sort -n | tail -n 3
0.9243826799526542
0.9780827495319969
0.9891715845993947
```

## Installation

```
pip install argsearch
```

## Usage

`argsearch` has 3 mandatory arguments:
 - A **search strategy** (`random`, `grid`, or `repeat`) and its configuration:
    - For `random`: **trials**, the number of random trials to run.
    - For `grid`: **divisions**, the number of points to try in each numeric range.
    - For `repeat`: **repeats**, the number of times to repeat the command.
 - A **command string** with **templates** designated by bracketed names (e.g. `'python my_script.py --flag {value}'`.
 -  A **range** for each template in the command string (e.g. `--value 1 100`).

Then, `argsearch` runs the command string several times, each time replacing the templates with values from their associated ranges.

Any optional arguments (`--num-workers`, `--output-json`, or `--disable-bar`) must appear before these.
I recommend you single-quote the command string to avoid shell expansion issues. Templates may appear multiple times in the command string (e.g. to name an experiment's output directory after its hyperparameters).

### Search Strategies

The search strategy determines which commands get run by sampling from the ranges.
Three search strategies are currently implemented:
 - **Random search** samples uniformly randomly from specified ranges for a fixed number of trials.
 - **Grid search** divides each numeric range into a fixed number of evenly-spaced points and runs once for each possible combination of inputs.
 - **Repeat** runs the same command a fixed number of times, and does not accept templates.

### Ranges

For each template that appears in the command string, you must provide a range that determines what values may be substituted into the template.
Three types of ranges are available:
 - **Floating-point ranges** are specified by a minimum and maximum floating-point value (e.g. `--value 0.0 1.0`).
 - **Integer ranges** are specified by a minimum and maximum integer (e.g. `--value 1 100`). Integer ranges are guaranteed to only yield integer values.
 - **Categorical ranges** are specified by a list of non-numeric categories, or more than two numbers (e.g. `--value A B C`, `--value 2 4 8 16`). Categorical ranges only draw values from the listed categories, and are not divided up during a grid search.
 
### Output

By default, `argsearch` streams each command's output to the standard output/error streams as soon as it's available. 
With the `--output-json` flag, `argsearch` will instead collect all output into a JSON string, printed to `stdout` at the end of the run.
This JSON data can be pretty-printed or wrangled with [`jq`](https://stedolan.github.io/jq/) for use in shell pipelines. 

### Multiprocessing

Providing `--num-workers N` runs commands in parallel with N worker processes. In this case, output will only appear on the standard streams once each command's done, to avoid mixing output from different runs. The format remains the same, but results are not guaranteed to come back in any particular order.

### License
`argsearch` is licensed under the MIT License.
