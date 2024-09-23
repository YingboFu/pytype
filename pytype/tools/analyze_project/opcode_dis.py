import dis
import types
import os
from collections import Counter


def count_opcodes(bytecode):
    """
    Recursively count opcodes in a given bytecode object.
    """
    counter = Counter()

    # Iterate over all instructions in the bytecode
    for instruction in dis.get_instructions(bytecode):
        counter[instruction.opname] += 1

        # Check if the instruction's argument is a code object
        if isinstance(instruction.argval, types.CodeType):
            counter += count_opcodes(instruction.argval)

    return counter


def count_opcodes_from_file(file_path):
    with open(file_path, 'r') as file:
        source_code = file.read()

    try:
        # Compile source code into bytecode
        bytecode = compile(source_code, file_path, 'exec')
        # Get opcode counts recursively
        opcode_counter = count_opcodes(bytecode)
    except SyntaxError:
        opcode_counter = Counter()

    return opcode_counter


def get_all_files_recursively(path):
    all_files = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.py'):
                all_files.append(os.path.join(root, file))
    return all_files


def get_src_path():
    dataset_dir = "/Users/fuyingbo/Desktop/dataset"
    src_paths = ["/Users/fuyingbo/Desktop/dataset/rocky---python-uncompyle6/uncompyle6",
                 "/Users/fuyingbo/Desktop/dataset/tf-coreml---tf-coreml/tfcoreml",
                 "/Users/fuyingbo/Desktop/dataset/aquasecurity---kube-hunter/kube_hunter",
                 "/Users/fuyingbo/Desktop/dataset/influxdata---influxdb-python/influxdb"]
    for dir in os.listdir(dataset_dir):
        if not dir.startswith('.'):
            project_name = dir.split('---')[1]
            if os.path.exists(os.path.join(dataset_dir, dir, project_name)):
                src_paths.append(os.path.join(dataset_dir, dir, project_name))
            elif os.path.exists(os.path.join(dataset_dir, dir, 'src')):
                src_paths.append(os.path.join(dataset_dir, dir, 'src'))
    return src_paths


if __name__ == "__main__":
    percentage_list = []
    for src_path in get_src_path():
        opcode_counts = Counter()
        all_files = get_all_files_recursively(src_path)
        for file in all_files:
            opcode_counts += count_opcodes_from_file(file)

        total_count = sum(opcode_counts.values())
        percentage_list.append({key: (value / total_count) * 100 for key, value in opcode_counts.items()})

    total_percentage = {}
    for d in percentage_list:
        for key, value in d.items():
            if key in total_percentage:
                total_percentage[key] += value
            else:
                total_percentage[key] = value

    num_dicts = len(percentage_list)
    average_percentage = {key: total / num_dicts for key, total in total_percentage.items()}

    finished_files = ['/Users/fuyingbo/Desktop/test_project/tox/src/tox/config/loader/str_convert.py',
                      '/Users/fuyingbo/Desktop/test_project/tox/src/tox/config/loader/stringify.py',
                      '/Users/fuyingbo/Desktop/test_project/tox/src/tox/config/loader/section.py']
    finished_opcode_counts = Counter()
    for finished_file in finished_files:
        finished_opcode_counts += count_opcodes_from_file(finished_file)
    print(f"{len(finished_opcode_counts)} finished opcodes")

    total_perc = 0
    for opcode, perc in sorted(average_percentage.items(), key=lambda item: item[1], reverse=True):
        if opcode in finished_opcode_counts:
            total_perc += perc
    print(f"Total opcode percentage: {total_perc:.2f}")
