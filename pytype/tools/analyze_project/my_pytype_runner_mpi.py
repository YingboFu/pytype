from mpi4py import MPI
import os
import subprocess

def work(cmd):
    """Execute the command using subprocess."""
    subprocess.run(cmd)

def gather_python_files(project_dir):
    """Recursively gather all Python files in the given directory."""
    python_files = []
    for root, dirs, files in os.walk(project_dir):
        for name in files:
            if name.endswith(".py"):
                python_files.append(os.path.join(root, name))
    return python_files

def main():
    """Main function to distribute and execute tasks using MPI."""
    # Initialize MPI
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    # Define the project directory
    project = '/Users/fuyingbo/Desktop/test_git_blame/tox/src'

    # Rank 0 gathers all Python files
    if rank == 0:
        python_files = gather_python_files(project)
        cmds = [
            ["pytype", "-o", f"{file[:file.rfind('/') + 1]}.pytype-{file[file.rfind('/') + 1:][:-3]}", file]
            for file in python_files
        ]
    else:
        cmds = None

    # Broadcast the commands to all processes
    cmds = comm.bcast(cmds, root=0)

    # Distribute tasks among processes
    local_cmds = [cmd for i, cmd in enumerate(cmds) if i % size == rank]

    # Each process executes its assigned commands
    for cmd in local_cmds:
        work(cmd)

    # Synchronize processes
    comm.Barrier()


if __name__ == '__main__':
    main()
