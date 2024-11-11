#!/usr/bin/env python3

import os
import subprocess
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm

NUM_PARALLEL = 16

HOME = "/home/sbrantq"
ENZYME_PATH = os.path.join(HOME, "sync/Enzyme/build/Enzyme/ClangEnzyme-15.so")
LLVM_PATH = os.path.join(HOME, "llvms/llvm15/build/bin")
CXX = os.path.join(LLVM_PATH, "clang++")

CXXFLAGS = [
    "-O3",
    "-Wall",
    f"-I{os.path.join(HOME, 'include')}",
    f"-L{os.path.join(HOME, 'lib')}",
    "-I/usr/include/c++/11",
    "-I/usr/include/x86_64-linux-gnu/c++/11",
    "-L/usr/lib/gcc/x86_64-linux-gnu/11",
    "-fno-exceptions",
    f"-fpass-plugin={ENZYME_PATH}",
    "-Xclang",
    "-load",
    "-Xclang",
    ENZYME_PATH,
    "-lmpfr",
    "-ffast-math",
    "-fno-finite-math-only",
    "-fuse-ld=lld",
]

FPOPTFLAGS_BASE = [
    "-mllvm",
    "--enzyme-enable-fpopt",
    "-mllvm",
    "--enzyme-print-herbie",
    "-mllvm",
    "--enzyme-print-fpopt",
    "-mllvm",
    "--fpopt-log-path=eig.txt",
    "-mllvm",
    "--fpopt-target-func-regex=eig",
    "-mllvm",
    "--fpopt-enable-solver",
    "-mllvm",
    "--fpopt-enable-pt",
    "-mllvm",
    "--fpopt-comp-cost-budget={budget}",
    "-mllvm",
    "--fpopt-num-samples=1000",
    "-mllvm",
    "--fpopt-cost-model-path=cm.csv",
]

BUDGETS = [
    # ?
]

LOG_DIR = "logs"
OUTPUT_DIR = "tmp"

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_command(command, log_file):
    """
    Runs a shell command and logs the output.
    """
    try:
        with open(log_file, "w") as f:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True)
            f.write(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        with open(log_file, "a") as f:
            f.write("\nError:\n")
            f.write(e.stdout)
        return False


def compile_fpopt(budget):
    fpopt_flags = FPOPTFLAGS_BASE.copy()
    fpopt_flags = [
        flag if flag != "--fpopt-comp-cost-budget={budget}" else f"--fpopt-comp-cost-budget={budget}"
        for flag in fpopt_flags
    ]

    command = [CXX] + CXXFLAGS + fpopt_flags + ["eig.cpp", "-o", os.path.join(OUTPUT_DIR, f"eig-fpopt-{budget}.exe")]

    log_file = os.path.join(LOG_DIR, f"compile_fpopt_{budget}.log")

    success = run_command(command, log_file)

    return (budget, success, log_file)


def main():
    num_workers = NUM_PARALLEL

    print(
        f"Starting compilation of eig-fpopt.exe with {len(BUDGETS)} budgets using {num_workers} parallel workers."
    )

    compiled = []
    failed = []

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_budget = {executor.submit(compile_fpopt, budget): budget for budget in BUDGETS}

        for future in tqdm(as_completed(future_to_budget), total=len(future_to_budget), desc="Compiling"):
            budget = future_to_budget[future]
            try:
                bud, success, log = future.result()
                if success:
                    compiled.append(budget)
                else:
                    failed.append(budget)
            except Exception as exc:
                print(f"Budget {budget} generated an exception: {exc}")
                failed.append(budget)

    print("\nCompilation Summary:")
    print(f"Total Budgets: {len(BUDGETS)}")
    print(f"Successfully Compiled: {len(compiled)}")
    print(f"Failed Compilations: {len(failed)}")

    if failed:
        print("\nFailed Budgets:")
        for budget in failed:
            print(f"  - {budget} (See {os.path.join(LOG_DIR, f'compile_fpopt_{budget}.log')})")

    print(f"\nCompiled binaries are located in the '{OUTPUT_DIR}' directory.")
    print(f"Compilation logs are located in the '{LOG_DIR}' directory.")


if __name__ == "__main__":
    main()
