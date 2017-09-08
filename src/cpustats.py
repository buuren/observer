import os


class CPUStats:
    def __init__(self, observer):
        self.observer = observer
        self.my_metric_key = "cpustats"
        self.my_file_list = ["stat"]
        self.observer.proc_file_dictionary.append(self.my_file_list)

        self.observer.calculated_values[self.my_metric_key] = dict()
        self.observer.raw_values[self.my_metric_key] = dict()
        self.observer.proc_instances[self.my_metric_key] = self
        self.keep_filenames = dict()

    def calculate_values(self, index):
        cpu_stats = dict()
        cpu_last = self.generate_counters(index)
        cpu_curr = self.generate_counters(index + 1)

        for device in cpu_curr.keys():
            calculations = {
                k: round(v, self.observer.r_prec) for k, v in self.cpustats_calc(
                    last=cpu_last[device],
                    curr=cpu_curr[device]
                ).items()
            }
            cpu_stats[device] = calculations

        self.observer.raw_values[self.my_metric_key][index] = cpu_stats

    def generate_counters(self, index):
        read_cpu_stats = self.observer.file_content[index][self.my_metric_key]['/proc/stat'][:os.cpu_count()+1]
        cpu_stats = [self.parse_cpustats(line) for line in read_cpu_stats]
        cpu_stats = {stat['dev']: stat for stat in cpu_stats}
        return cpu_stats

    def get_deltams(self, index):
        cpu_last = self.generate_counters(index)['cpu']
        cpu_curr = self.generate_counters(index + 1)['cpu']

        curr_cpu_load = int(cpu_curr['user']) + int(cpu_curr['system']) + \
            int(cpu_curr['idle']) + int(cpu_curr['iowait'])

        last_cpu_load = int(cpu_last['user']) + int(cpu_last['system']) + \
            int(cpu_last['idle']) + int(cpu_last['iowait'])

        hz = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
        deltams = 1000 * (int(curr_cpu_load) - int(last_cpu_load)) / os.cpu_count() / hz
        return deltams

    @staticmethod
    def cpustats_calc(last, curr):
        cpu_stats = {}

        deltas = {stat: int(curr[stat]) - int(last[stat]) for stat in curr.keys() if stat is not "dev"}
        sum_deltas = sum([deltas[stat_delta] for stat_delta in deltas.keys()])

        def calc_deltas(field):
            return float(deltas[field]) / sum_deltas * 100

        cpu_stats['%usr'] = calc_deltas('user')
        cpu_stats['%nice'] = calc_deltas('nice')
        cpu_stats['%sys'] = calc_deltas('system')
        cpu_stats['%iowait'] = calc_deltas('iowait')
        cpu_stats['%irq'] = calc_deltas('irq')
        cpu_stats['%soft'] = calc_deltas('softirq')
        cpu_stats['%steal'] = calc_deltas('steal')
        cpu_stats['%guest'] = calc_deltas('guest')
        cpu_stats['%gnice'] = calc_deltas('guest_nice')
        cpu_stats['%idle'] = calc_deltas('idle')

        return cpu_stats

    @staticmethod
    def parse_cpustats(line):
        dev, user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice = line.split()
        del line
        d = {k: v for k, v in locals().items()}
        return d

    def return_proc_location(self, index):
        list_of_filenames = ['/proc/%s' % filename for filename in self.my_file_list]
        self.keep_filenames[index] = list_of_filenames
        return list_of_filenames
