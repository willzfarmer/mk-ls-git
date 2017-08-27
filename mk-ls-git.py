import os
import subprocess
import sys
import termios

from mklibpy.common.string import AnyString
from mklibpy.terminal.colored_text import get_text
from mklibpy.util.path import CD

__author__ = 'Michael'


def system_call(*args, **kwargs):
    out = subprocess.check_output(*args, **kwargs)
    return out.decode().splitlines(False)


def is_git_repo(abspath):
    path = os.path.join(abspath, ".git")
    return os.path.exists(path) and os.path.isdir(path)


def get_git_branch(abspath):
    with CD(abspath):
        for line in system_call(['git', 'branch']):
            sp = line.split()
            if "*" not in sp:
                continue
            return sp[1]


class LsGit(object):
    def __init__(self, stdout=None):
        self.__stdout = stdout
        if stdout is None:
            self.__stdout = sys.stdout

    @property
    def is_tty(self):
        try:
            termios.tcgetattr(self.__stdout)
        except termios.error:
            return False
        else:
            return True

    @property
    def is_gnu(self):
        try:
            system_call(['ls', '--version'], stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            return False
        else:
            return True

    def print(self, *args, **kwargs):
        print(*args, **kwargs, file=self.__stdout)

    def __call__(self, *args):
        LsGitProcess(self, args).run()


class LsGitProcess(object):
    def __init__(self, parent, args):
        self.__parent = parent
        self.__args = args

        self.__options = None
        self.__dirs = None
        self.__cur_dir = None

        self.__parse_args()

    def __parse_args(self):
        self.__options = [arg for arg in self.__args if arg.startswith('-')]
        self.__dirs = [arg for arg in self.__args if not arg.startswith('-')]

    @property
    def __color(self):
        if not self.__parent.is_tty:
            return False
        options = AnyString(self.__options)
        if self.__parent.is_gnu:
            return 'C' in options or options.startswith('--color')
        else:
            return 'G' in options

    def color(self, text, color=None, mode=None):
        if not self.__color:
            return text
        return get_text(text, color=color, mode=mode)

    def __process_line(self, line):
        if line.endswith(':') and line[:-1] in self.__dirs:
            self.__cur_dir = line[:-1]
            return line

        sp = line.split()
        if len(sp) < 9:
            return line

        dir = sp[8]
        abspath = os.path.abspath(os.path.join(self.__cur_dir, dir))
        if not is_git_repo(abspath):
            return line

        branch = get_git_branch(abspath)
        return line + self.color(" ({})".format(branch), color='red', mode='bold')

    def run(self):
        if self.__dirs:
            self.__cur_dir = self.__dirs[0]
        else:
            self.__cur_dir = os.getcwd()

        for line in system_call(['ls', '-l'] + list(self.__args)):
            self.__parent.print(self.__process_line(line))


def main(args=None):
    if args is None:
        import sys
        args = sys.argv[1:]

    instance = LsGit()
    try:
        instance(*args)
    except subprocess.CalledProcessError as e:
        exit(e.returncode)


if __name__ == '__main__':
    main()
