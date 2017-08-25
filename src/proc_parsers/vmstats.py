class VMStats:
    def __init__(self, observer):
        self.observer = observer
        self.my_metric_key = "vmstats"
        self.observer.calculated_values[self.my_metric_key] = dict()
        self.observer.raw_results[self.my_metric_key] = dict()

    def get_vmstats(self, index):
        vmstats = self.vmstat_counters(index)
        self.observer.raw_results[self.my_metric_key][index] = vmstats

    def vmstat_counters(self, index):
        read_loadvg = self.observer.file_content[index]['/proc/loadavg'][0]
        read_vmstat = self.observer.file_content[index]['/proc/vmstat']
        read_meminfo = self.observer.file_content[index]['/proc/meminfo']

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
