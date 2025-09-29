import subprocess, time, logging
LOG = logging.getLogger("gaspipe.subproc")

def run_cmd(cmd, timeout=3600, retries=3, backoff=2.0, env=None):
    attempt = 0
    while attempt <= retries:
        try:
            LOG.debug({"cmd": cmd, "attempt": attempt})
            res = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout, env=env)
            return res.stdout
        except subprocess.CalledProcessError as e:
            LOG.error({"cmd": cmd, "returncode": e.returncode, "stderr": e.stderr})
            if attempt == retries:
                raise
            attempt += 1
            time.sleep(backoff ** attempt)
