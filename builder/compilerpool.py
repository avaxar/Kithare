"""
This file is a part of the Kithare programming language source code.
The source code for Kithare programming language is distributed under the MIT
license.
Copyright (C) 2022 Kithare Organization

builder/compilerpool.py
Defines a CompilerPool class to compile multiple source files concurrently
using a subprocess pool
"""


import subprocess
import time
from pathlib import Path
from typing import Optional, Sequence

from .cflags import CompilerFlags
from .constants import CPU_COUNT
from .utils import BuildError


class CompilerPool:
    """
    A pool of source files to be compiled in multiple subprocesses
    """

    def __init__(self, maxpoolsize: Optional[int], cflags: CompilerFlags):
        """
        Initialise CompilerPool instance. maxpoolsize is the limit on number of
        subprocesses that can be opened at a given point. If not specified
        (None), defaults to number of cores on the machine. The cflags arg is
        the compiler flags to be passed
        """
        self.cflags = cflags

        self._procs: dict[Path, subprocess.Popen[str]] = {}
        self._queued_procs: list[tuple[Path, Path]] = []
        self.failed: bool = False

        self.maxpoolsize = CPU_COUNT + 2 if maxpoolsize is None else maxpoolsize

    def _start_proc(self, cfile: Path, ofile: Path):
        """
        Internal function to start a compile subprocess
        """
        # pylint: disable=consider-using-with
        self._procs[cfile] = subprocess.Popen(
            (
                self.cflags.get_compiler(cfile.suffix),
                "-o",
                str(ofile),
                "-c",
                str(cfile),
                *self.cflags.flags_by_ext(cfile.suffix),
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )

    def _finish_proc(self, proc: subprocess.Popen):
        """
        Take a finished Popen subprocess, print command name, stdout and
        error code
        """
        # stderr is redirected to stdout here
        try:
            stdout, _ = proc.communicate()
        except ValueError:
            # can happen during a KeyboardInterrupt
            return

        if isinstance(proc.args, bytes):
            print(">", proc.args.decode())
        elif isinstance(proc.args, Sequence) and not isinstance(proc.args, str):
            print(">", *proc.args)
        else:
            print(">", proc.args)

        if proc.returncode:
            print(stdout, end="")
            print(f"g++ exited with error code: {proc.returncode}\n")
            self.failed = True
        else:
            print(stdout)

    def update(self, start_new: bool = True):
        """
        Runs an "update" operation. Any processes that have been finished are
        removed from the process pool after the subprocess output has been
        printed along with the return code (on error). Starts a new subprocess
        from the queued pending process pool.
        """
        for cfile, proc in tuple(self._procs.items()):
            if proc.poll() is None:
                # proc is still running
                continue

            print(f"Building file: {cfile}")
            self._finish_proc(proc)
            self._procs.pop(cfile)

            # start a new process from queued process
            if self._queued_procs and start_new:
                self._start_proc(*self._queued_procs.pop())

    def add(self, cfile: Path, ofile: Path):
        """
        Add a source file to be compiled into the compiler pool. cfile is the
        Path object to the source file, while ofile is the Path object to the
        output file
        """
        if len(self._procs) >= self.maxpoolsize:
            # pool is full, queue the command
            self._queued_procs.append((cfile, ofile))
        else:
            self._start_proc(cfile, ofile)

        # call an update
        self.update()

    def poll(self):
        """
        Returns False when all files in the pool finished compiling, True
        otherwise
        """
        return bool(self._queued_procs or self._procs)

    def wait(self, timeout: int = 300):
        """
        Block until all queued files are compiled. A timeout arg is used to
        kill builds if they take too much time.
        """
        start_time = time.perf_counter()
        try:
            while self.poll():
                self.update()
                time.sleep(0.005)

                if time.perf_counter() >= start_time + timeout:
                    # hit timeout, quit wait
                    raise BuildError(f"Hit build timeout of {timeout} s")

        finally:
            # gracefully terminate subprocesses on errors like KeyboardInterrupt
            self.update(start_new=False)
            for proc in self._procs.values():
                proc.terminate()
