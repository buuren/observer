import os
from observer import Observer


class PidStats:
    def __init__(self, observer):
        self.observer = observer
        self.my_metric_key = "pid_data"
        self.observer.proc_instances[self.my_metric_key] = self
        self.observer.calculated_values[self.my_metric_key] = dict()
        self.observer.raw_values[self.my_metric_key] = dict()

    def calculate_values(self, index):
        self.observer.raw_values[self.my_metric_key][index] = self.generate_counters(index)

    def generate_counters(self, index):
        counters = dict()
        for pid in self.observer.file_content[index]['pid']:
            counters[pid] = dict()
            for pid_filename in self.observer.pid_file_list:
                counters[pid][pid_filename] = self.parse_pid_filename(index, pid, pid_filename)

        return counters

    def parse_pid_filename(self, index, pid, pid_filename):
        proc_dict = dict()

        for line in self.observer.file_content[index]['pid'][pid][pid_filename]:
            proc_dict[line.strip().split()[0].replace(":", "")] = ''.join(line.strip().split()[1:])

        return proc_dict

if __name__ == '__main__':
    pass
