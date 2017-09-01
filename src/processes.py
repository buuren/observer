import os
from observer import Observer


class Processes:
    def __init__(self, observer):
        self.observer = observer
        self.my_metric_key = "processes"
        self.observer.proc_instances[self.my_metric_key] = self
        self.observer.calculated_values[self.my_metric_key] = dict()
        self.observer.raw_values[self.my_metric_key] = dict()

    def calculate_values(self, index):
        self.observer.raw_values[self.my_metric_key][index] = {"process": {"test": 10}}

    def return_pid_list(self):
        return [pid for pid in os.listdir('/proc') if pid.isdigit()]

        #for pid in pids:

            #try:
            #    print(open(os.path.join('/proc', pid, 'cmdline'), 'rb').read())
            #except IOError:  # proc has already terminated
            #    continue

if __name__ == '__main__':
    observer = Observer(count=2, sleep=2)
    Processes(observer).return_pid_list()