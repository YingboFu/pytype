import os
import multiprocessing
import subprocess


def work(cmd):
    subprocess.run(cmd)


def main():
    python_files = []
    project = '/Users/fuyingbo/Desktop/test_git_blame/tox/src'
    for root, dirs, files in os.walk(project):
        for name in files:
            if name.endswith(".py"):
                python_files.append(os.path.join(root, name))
    cmds = []
    for file in python_files:
        output = file[:file.rfind('/') + 1] + '.pytype-' + file[file.rfind('/') + 1:][:-3]
        cmds.append(["pytype", "-o", output, file])
    count = multiprocessing.cpu_count() - 1
    pool = multiprocessing.Pool(processes=count)
    for cmd in cmds:
        pool.apply_async(work, args=(cmd,))
    pool.close()
    pool.join()


if __name__ == '__main__':
    main()
