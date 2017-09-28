class VMStats:
    def __init__(self, observer):
        self.observer = observer
        self.metric_key = "vmstats"
        self.file_list = ["vmstat", "meminfo", "loadavg"]
        self.keep_filenames = dict()
        self.observer.proc_file_dictionary.append(self.file_list)
        self.observer.calculated_values[self.metric_key] = dict()
        self.observer.raw_values[self.metric_key] = dict()
        self.observer.proc_instances[self.metric_key] = self


    def calculate_values(self, index):
        vmstats = self.generate_counters(index)
        self.observer.raw_values[self.metric_key][index] = vmstats

    def generate_counters(self, index):
        read_loadvg = self.observer.file_content[index][self.metric_key]['/proc/loadavg'][0]
        read_vmstat = self.observer.file_content[index][self.metric_key]['/proc/vmstat']
        read_meminfo = self.observer.file_content[index][self.metric_key]['/proc/meminfo']

        vmstats = dict()
        vmstats['loadavg'] = self.parse_loadavg(read_loadvg)
        vmstats['vmstat'] = {stat.split()[0]: int(stat.split()[1]) for stat in read_vmstat}
        vmstats['meminfo'] = {
            line.split()[0].replace(":", ""): round(int(line.split()[1])/1024/1024, self.observer.r_prec)
            for line in read_meminfo
        }

        return vmstats

    @staticmethod
    def parse_loadavg(line):
        load_1_min, load_5_min, load_15_min, curr_proc, last_proc_id = line.split()
        proc_scheduled = curr_proc.split('/')[0]
        entities_total = curr_proc.split('/')[1]
        del line, curr_proc, last_proc_id
        d = {k: float(v) for k, v in locals().items()}
        return d

    def return_proc_location(self, index):
        list_of_filenames = ['/proc/%s' % filename for filename in self.file_list]
        self.keep_filenames[index] = list_of_filenames
        return list_of_filenames
