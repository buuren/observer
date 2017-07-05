def json_reader(file_name):
    import json

    def find_all_with_key(wanted_key, tree, path=tuple()):
        if isinstance(tree, list):
            for idx, el in enumerate(tree):
                yield from find_all_with_key(wanted_key, el, path + (idx,))
        elif isinstance(tree, dict):
            for k in tree:
                if k == wanted_key:
                    yield path + (k,)
            for k, v in tree.items():
                yield from find_all_with_key(wanted_key, v, path + (k,))

    with open(file_name) as data_file:
        data = json.load(data_file)

    return data


def bin_verify(bin_data):
    import shutil
    import subprocess
    install_list = []

    for executable in bin_data:
        if shutil.which(executable) is None:
            print("Unable to find binary: [%s]" % executable)
            required_package = bin_data[executable]['requires']['package']

            if required_package not in install_list:
                install_list.append(required_package)

    if len(install_list) > 0:
        print("Installing packages: %s" % install_list)
        completed = subprocess.run('yum -y install %s' % ' '.join(install_list), shell=True)
        print('returncode:', completed.returncode)

if __name__ == '__main__':
    json_reader("../config/centos7.json")
