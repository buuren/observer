import subprocess
import sys


class IOStatError(Exception):
    pass


class CmdError(IOStatError):
    pass


class ParseError(IOStatError):
    pass


class BinaryRunner:
    def __init__(self):
        pass

    @staticmethod
    def shell_run(command):
        close_fds = 'posix' in sys.builtin_module_names

        return subprocess.Popen(
            command,
            bufsize=1,
            shell=True,
            stdout=subprocess.PIPE,
            close_fds=close_fds
        )

    @staticmethod
    def get_command_output(child):
        (stdout, stderr) = child.communicate()
        ecode = child.poll()

        if ecode != 0:
            raise CmdError('Command %r returned %d' % (child.cmd, ecode))

        return stdout.decode('utf-8').strip()

if __name__ == '__main__':
    pass
