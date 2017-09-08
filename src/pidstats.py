import os
from observer import Observer


class PidStats:
    def __init__(self, observer):
        self.observer = observer
        self.my_metric_key = "pid_data"
        self.my_file_list = ["io", "status", "maps", "smaps", "statm"]
        self.observer.proc_file_dictionary.append(self.my_file_list)

        self.observer.calculated_values[self.my_metric_key] = dict()
        self.observer.raw_values[self.my_metric_key] = dict()
        self.observer.proc_instances[self.my_metric_key] = self

        self.keep_filenames = dict()
        self.keep_pids = dict()

    def calculate_values(self, index):
        self.observer.raw_values[self.my_metric_key][index] = self.generate_counters(index)

    def generate_counters(self, index):
        counters = dict()
        for pid in self.keep_pids[index]:
            counters[pid] = dict()
        #for pid_filename in self.observer.file_content[index][self.my_metric_key]:
            for pid_filename in self.my_file_list:
                counters[pid][pid_filename] = self.parse_pid_filename(index, pid, '/proc/%s/%s' % (pid, pid_filename))

        return counters

    def parse_pid_filename(self, index, pid, pid_filename):
        proc_dict = dict()

        for line in self.observer.file_content[index][self.my_metric_key][pid_filename]:
            proc_dict[line.strip().split()[0].replace(":", "")] = ''.join(line.strip().split()[1:])

        return proc_dict

    def return_proc_location(self, index):
        pid_list = self.return_pid_list()

        list_of_filenames = [
            '/proc/%s/%s' % (pid, pid_filename)
            for pid in pid_list
            for pid_filename in self.my_file_list
        ]

        self.keep_filenames[index] = list_of_filenames
        self.keep_pids[index] = pid_list

        return list_of_filenames

    @staticmethod
    def return_pid_list():
        return [pid for pid in os.listdir('/proc') if pid.isdigit()]
if __name__ == '__main__':
    pass
