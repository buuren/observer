import os


class PidStats:
    def __init__(self, observer):
        self.observer = observer
        self.my_metric_key = "pid_data"
        self.my_file_list = ["io", "status", "smaps", "statm", "cmdline"]
        self.observer.proc_file_dictionary.append(self.my_file_list)

        self.observer.calculated_values[self.my_metric_key] = dict()
        self.observer.raw_values[self.my_metric_key] = dict()
        self.observer.proc_instances[self.my_metric_key] = self

        self.keep_filenames = dict()
        self.keep_pids = dict()

    def calculate_values(self, index):
        counters = self.parse_proc_files(index)
        calculations = self.calculate_counters(counters)
        self.observer.raw_values[self.my_metric_key][index] = calculations

    def parse_proc_files(self, index):
        pid_stats = dict()

        for pid in self.keep_pids[index]:
            pid_stats[pid] = dict()
            pid_stats[pid]["io"] = self.parse_io(index, "/proc/%s/io" % pid)
            pid_stats[pid]["status"] = self.parse_status(index, "/proc/%s/status" % pid)
            pid_stats[pid]["smaps"] = self.parse_smaps(index, "/proc/%s/smaps" % pid)
            pid_stats[pid]["statm"] = self.parse_statm(index, "/proc/%s/statm" % pid)
            pid_stats[pid]["cmdline"] = self.parse_cmdline(index, "/proc/%s/cmdline" % pid)

        return pid_stats

    def calculate_counters(self, counters):
        calculated_values = dict()
        for pid in counters.keys():
            calculated_values[pid] = dict()
            calculated_values[pid]['memory'] = self.calculate_memory(counters[pid])
            calculated_values[pid]['cmdline'] = counters[pid]['cmdline']
            print(counters[pid]['cmdline'])
        return calculated_values

    def calculate_memory(self, pid_counters):
        # https://github.com/pixelb/ps_mem/blob/master/ps_mem.py
        pss_adjust = 0.5

        private = []
        shared = []
        pss = []
        swap = []
        swap_pss = []

        for thread in pid_counters['smaps']:
            thread_memory_data = pid_counters['smaps'][thread]
            shared.extend([
                thread_memory_data['Shared_Clean:'],
                thread_memory_data['Shared_Dirty:'],
                thread_memory_data['Shared_Hugetlb:']
            ])
            private.extend([
                thread_memory_data['Private_Clean:'],
                thread_memory_data['Private_Dirty:'],
                thread_memory_data['Private_Hugetlb:']
            ])
            pss.append(thread_memory_data['Pss:']+pss_adjust)
            swap.append(thread_memory_data['Swap:'])
            swap_pss.append(thread_memory_data['SwapPss:'])

        private_sum = sum(private)
        pss_sum = sum(pss)
        shared_sum = pss_sum - private_sum
        swap_sum = sum(swap_pss)

        return {"private": private_sum, "shared": shared_sum, "swap": swap_sum}

    def parse_cmdline(self, index, pid_filename):
        cmdline = self.observer.file_content[index][self.my_metric_key][pid_filename]

        if len(cmdline) > 0:
            cmdline_split = cmdline[0].split("\0")
            return {cmdline_split[0]: cmdline_split[1:-1]}
        else:
            return {}

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
        smaps = {}

        for chunk in chunked_file:
            smaps[chunk[0]] = dict()
            for n in range(1, 20):
                smaps[chunk[0]][chunk[n].split()[0]] = int(chunk[n].split()[1])
            smaps[chunk[0]][chunk[20].split()[0]] = chunk[20].split()[1:]

        return smaps

    def parse_statm(self, index, pid_filename):
        file_content = self.observer.file_content[index][self.my_metric_key][pid_filename]
        size, rss, shared, text, lib, data, dt = file_content[0].split()
        del self, index, pid_filename, file_content

        return {
            k: v
            for k, v in locals().items()
        }

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
