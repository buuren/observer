import os
from observer import Observer


class PidStats:
    def __init__(self, observer):
        self.observer = observer
        self.my_metric_key = "pid_data"
        # "maps",
        self.my_file_list = ["io", "status", "smaps", "statm"]
        #self.my_file_list = ["io", "status", "maps", "smaps", "statm"]
        self.observer.proc_file_dictionary.append(self.my_file_list)

        self.observer.calculated_values[self.my_metric_key] = dict()
        self.observer.raw_values[self.my_metric_key] = dict()
        self.observer.proc_instances[self.my_metric_key] = self

        self.keep_filenames = dict()
        self.keep_pids = dict()

    def calculate_values(self, index):
        # Parse PID files
        pid_stats = dict()
        pid_stats = self.generate_counters(index)
        calculations = dict()
        # self.observer.raw_values[self.my_metric_key][index] = self.generate_counters(index)

        # Start calculations
        exit()
        self.observer.raw_values[self.my_metric_key][index] = calculations

    def generate_counters(self, index):
        pid_stats = dict()

        for pid in self.keep_pids[index]:
            pid_stats[pid] = dict()
            pid_stats[pid]["io"] = self.parse_io(index, "/proc/%s/io" % pid)
            pid_stats[pid]["status"] = self.parse_status(index, "/proc/%s/status" % pid)
            pid_stats[pid]["smaps"] = self.parse_smaps(index, "/proc/%s/smaps" % pid)
            pid_stats[pid]["statm"] = self.parse_statm(index, "/proc/%s/statm" % pid)

        return pid_stats

    def parse_io(self, index, pid_filename):
        return {
            line.strip().split()[0].replace(":", ""): ''.join(line.strip().replace('kB', '').split()[1:])
            for line in self.observer.file_content[index][self.my_metric_key][pid_filename]
        }

    def parse_status(self, index, pid_filename):
        return {
            line.strip().split()[0].replace(":", ""): ''.join(line.strip().replace('kB', '').split()[1:])
            for line in self.observer.file_content[index][self.my_metric_key][pid_filename]
        }

    def parse_smaps(self, index, pid_filename):
        file_content = self.observer.file_content[index][self.my_metric_key][pid_filename]
        chunked_file = [file_content[i:i + 21] for i in range(0, len(file_content), 21)]

        return {
            chunk[0]: {
                    chunk[n].split()[0]: chunk[n].split()[1:]
            } for n in range(1, 21)
            for chunk in chunked_file
        }

    def parse_statm(self, index, pid_filename):
        file_content = self.observer.file_content[index][self.my_metric_key][pid_filename]

        size, resident, shared, text, lib, data, dt = file_content[0].split()
        del self, index, pid_filename, file_content

        return {
            k: v
            for k, v in locals().items()
        }


    def get_process_memory_stats(self, index):
        """
        based on  statm parser:

        size       (1) total program size (same as VmSize in /proc/[pid]/status)
        resident   (2) resident set size (same as VmRSS in /proc/[pid]/status)
        shared     (3) number of resident shared pages (i.e., backed by a file) (same as RssFile+RssShmem in /proc/[pid]/status)
        text       (4) text (code)
        lib        (5) library (unused since Linux 2.6; always 0)
        data       (6) data + stack
        dt         (7) dirty pages (unused since Linux 2.6; always 0)

        VmSize in status
        Shareds
        mem_ids
        swaps
        shared_swaps
        http://man7.org/linux/man-pages/man5/proc.5.html
        """
        #dict_keys(['io', 'status', 'maps', 'smaps', 'statm'])

        print(self.observer.raw_values[self.my_metric_key][index]['3334']['smaps'])
        exit()

        shared_mem = sum(
            [
                int(line.split()[1])
                for line in self.observer.raw_values[self.my_metric_key][index]
            ]
        )

        private_mem = sum(
            [int(line.split()[1]) for line in self.observer.raw_values[self.my_metric_key][index]]
        )

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
