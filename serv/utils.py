import os
import sys
import tempfile
import subprocess

PLATFORM = sys.platform
IS_WIN = (os.name == 'nt')
IS_DARWIN = (PLATFORM == 'darwin')
IS_LINUX = (PLATFORM == 'linux2')


def run(executable):
    stderr = subprocess.PIPE
    stdout = subprocess.PIPE
    proc = subprocess.Popen(
        executable,
        stdout=stdout,
        stderr=stderr)
    out, err = proc.communicate()
    return proc.returncode, out.rstrip(), err.rstrip()


def get_tmp_dir(init_system, application_name):
    tmp_application_dir = os.path.join(
        tempfile.gettempdir(), init_system + '-' + application_name)
    if not os.path.isdir(tmp_application_dir):
        os.makedirs(tmp_application_dir)
    return tmp_application_dir
