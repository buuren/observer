import os
import time


class Observer:
    def __init__(self, sleep, count):
        self.sleep = sleep
        self.count = count
        self.data = dict()

        self.proc_file_dictionary = {
            "f_diskstats": "/proc/diskstats",
            "f_partitions": "/proc/partitions",
            "f_stat": "/proc/stat",
            "f_loadavg": "/proc/loadavg"
        }

    def file_reader(self, index):
        print("Reading metrics...")
        for proc, file_name in self.proc_file_dictionary.items():
            with open(file_name) as f:
                self.data[index][proc] = f.readlines()
                self.data[index]['ts'] = os.stat(f.name).st_mtime

    def data_generator(self, sleep, count):
        assert count >= 2, 'Count must be equal or greater 2'

        print("Will generate [%s] metrics with [%s] seconds time interval" % (count, sleep))
        for index in range(1, count):
            self.data[index] = dict()
            self.file_reader(index)
            time.sleep(sleep)

        self.data[count] = dict()
        self.file_reader(count)

        return self.data

    def diskstats(self):
        disk_stats = DiskStats(sleep=self.sleep, count=self.count, observer_data=self.data)
        disk_stats.analyze_diskstats()

    def cpustats(self):
        cpu_stats = CPUStats(sleep=self.sleep, count=self.count, observer_data=self.data)
        cpu_stats.analyze_cpustats()

    def vmstats(self):
        vm_stats = VMStats(sleep=self.sleep, count=self.count, observer_data=self.data)
        vm_stats.analyze_vmstats()


class Constructor:
    def __init__(self, sleep, count, observer_data):
        self.sleep = sleep
        self.count = count

        if len(observer_data.keys()) == 0:
            self.observer_obj = Observer(self.sleep, self.count)
            self.observer_data = self.observer_obj.data_generator(self.sleep, self.count)
        else:
            self.observer_data = observer_data


class Processes(Constructor):
    def __init__(self, sleep, count, observer_data):
        super().__init__(sleep, count, observer_data)


class CPUStats(Constructor):
    def __init__(self, sleep, count, observer_data):
        super().__init__(sleep, count, observer_data)

    def analyze_cpustats(self):
        print("Starting to analyze CPU data...")
        cpu_stats = self.get_cpustats()
        for dev, counters in cpu_stats.items():
            print(dev, counters)

    def get_cpustats(self):
        result = {}
        for index in range(1, self.count):
            result[index] = {}
            cpu_last = self.cpu_io_counters(index)
            cpu_last_ts = self.observer_data[index]["ts"]

            cpu_curr = self.cpu_io_counters(index + 1)
            cpu_curr_ts = self.observer_data[index + 1]["ts"]

            cpu_stats = {}

            ts_delta = cpu_curr_ts - cpu_last_ts
            print("CPU statistics from [%s] to [%s] (Delta: %s ms)" % (
                time.strftime("%Z - %Y/%m/%d, %H:%M:%S", time.localtime(cpu_last_ts)),
                time.strftime("%Z - %Y/%m/%d, %H:%M:%S", time.localtime(cpu_curr_ts)),
                round(ts_delta, 4)
            ))
            print("---------------------------------------------------------------------------------------------------")

            for dev in cpu_curr.keys():
                calculations = {
                    k: round(v, 2) for k, v in self.cpustats_calc(
                        last=cpu_last[dev],
                        curr=cpu_curr[dev]
                    ).items()
                }
                cpu_stats[dev] = calculations
                print(dev, cpu_stats[dev])
                result[index] = cpu_stats

        return result

    def cpustats_calc(self, last, curr):
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

    def line_to_dict(self, line):
        dev, user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice = line.split()
        del line, self
        d = {k: v for k, v in locals().items()}
        return d

    def cpu_io_counters(self, index):
        read_cpu_stats = self.observer_data[index]['f_stat'][:os.cpu_count()+1]
        cpu_stats = [self.line_to_dict(line) for line in read_cpu_stats]
        cpu_stats = {stat['dev']: stat for stat in cpu_stats}
        return cpu_stats

    @staticmethod
    def get_deltams(cpu_last, cpu_curr):
        curr_cpu_load = int(cpu_curr['user']) + int(cpu_curr['system']) + \
            int(cpu_curr['idle']) + int(cpu_curr['iowait'])

        last_cpu_load = int(cpu_last['user']) + int(cpu_last['system']) + \
            int(cpu_last['idle']) + int(cpu_last['iowait'])

        hz = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
        deltams = 1000 * (int(curr_cpu_load) - int(last_cpu_load)) / os.cpu_count() / hz
        return deltams


class VMStats(Constructor):
    def __init__(self, sleep, count, observer_data):
        super().__init__(sleep, count, observer_data)

    def analyze_vmstats(self):
        vm_stats = self.get_vmstats()
        for dev, counters in vm_stats.items():
            print(dev, counters)

    def get_vmstats(self):
        result = {}
        for index in range(1, self.count):
            result[index] = {}
            curr_loadavg = self.loadavg_counters(index)
            result[index] = curr_loadavg

        return result

    def parse_loadavg(self, line):
        one_min, five_min, fifteen_min, curr_proc, last_proc_id = line.split()
        proc_scheduled = curr_proc.split('/')[0]
        entities_total = curr_proc.split('/')[1]
        del line, self, curr_proc
        d = {k: v for k, v in locals().items()}
        return d

    def loadavg_counters(self, index):
        read_loadvg = self.observer_data[index]['f_loadavg'][0]
        loadavg_stats = {"loadavg": self.parse_loadavg(read_loadvg)}
        return loadavg_stats


class DiskStats(Constructor):
    def __init__(self, sleep, count, observer_data):
        super().__init__(sleep, count, observer_data)
        self.sector_size = 1

    def analyze_diskstats(self):
        print("Starting to analyze data...")
        disk_stats = self.get_diskstats()
        for dev, counters in disk_stats.items():
            print(dev, counters)

    def get_diskstats(self):
        result = {}
        for index in range(1, self.count):
            result[index] = {}
            disk_last = self.disk_io_counters(index)
            disk_last_ts = self.observer_data[index]["ts"]

            disk_curr = self.disk_io_counters(index + 1)
            disk_curr_ts = self.observer_data[index + 1]["ts"]

            cpu_runner = CPUStats(1, 3, self.observer_data)
            cpu_last = cpu_runner.cpu_io_counters(index)
            cpu_curr = cpu_runner.cpu_io_counters(index + 1)

            deltams = cpu_runner.get_deltams(cpu_last['cpu'], cpu_curr['cpu'])

            disk_stats = {}

            ts_delta = disk_curr_ts - disk_last_ts
            print("Disk IO statistics from [%s] to [%s] (Delta: %s ms)" % (
                time.strftime("%Z - %Y/%m/%d, %H:%M:%S", time.localtime(disk_last_ts)),
                time.strftime("%Z - %Y/%m/%d, %H:%M:%S", time.localtime(disk_curr_ts)),
                round(ts_delta, 4)
            ))
            print("---------------------------------------------------------------------------------------------------")
            for dev in disk_curr.keys():
                calculations = {
                    k: round(v, 2) for k, v in self.calc(
                        last=disk_last[dev],
                        curr=disk_curr[dev],
                        ts_delta=ts_delta,
                        deltams=deltams
                    ).items()
                }
                disk_stats[dev] = calculations
                print(dev, disk_stats[dev])

                result[index] = disk_stats

        return result

    def calc(self, last, curr, ts_delta, deltams):
        disk_stats = {}

        def delta(field):
            return (int(curr[field]) - int(last[field])) / ts_delta

        disk_stats['rrqm/s'] = delta('r_merges')
        disk_stats['wrqm/s'] = delta('w_merges')
        disk_stats['r/s'] = delta('r_ios')
        disk_stats['w/s'] = delta('w_ios')
        disk_stats['iops'] = int(disk_stats['r/s']) + int(disk_stats['w/s'])
        disk_stats['rkB/s'] = delta('r_sec') * self.sector_size / 1024
        disk_stats['wkB/s'] = delta('w_sec') * self.sector_size / 1024
        disk_stats['avgrq-sz'] = 0
        disk_stats['avgqu-sz'] = delta('rq_ticks') / 1000

        if disk_stats['r/s'] + disk_stats['w/s'] > 0:
            disk_stats['avgrq-sz'] = (delta('r_sec') + delta('w_sec')) / (delta('r_ios') + delta('w_ios'))
            disk_stats['await'] = (delta('r_ticks') + delta('w_ticks')) / (delta('r_ios') + delta('w_ios'))
            disk_stats['r_await'] = delta('r_ticks') / delta('r_ios') if delta('r_ios') > 0 else 0
            disk_stats['w_await'] = delta('w_ticks') / delta('w_ios') if delta('w_ios') > 0 else 0
            disk_stats['svctm'] = delta('tot_ticks') / (delta('r_ios') + delta('w_ios'))
        else:
            disk_stats['avgrq-sz'] = 0
            disk_stats['await'] = 0
            disk_stats['r_await'] = 0
            disk_stats['w_await'] = 0
            disk_stats['svctm'] = 0

        blkio_ticks = int(curr["tot_ticks"]) - int(last["tot_ticks"])
        util = (100 * blkio_ticks / deltams) if (100 * blkio_ticks / deltams) < 100 else 100
        disk_stats['%util'] = util

        return disk_stats

    def parse_diskstats(self, line):
        major, minor, dev, r_ios, r_merges, r_sec, r_ticks, w_ios, w_merges, \
            w_sec, w_ticks, ios_pgr, tot_ticks, rq_ticks = line.split()

        del line, self
        d = {k: v for k, v in locals().items()}
        return d

    def disk_io_counters(self, index):
        read_partitions = self.observer_data[index]['f_partitions'][2:]
        partitions = set([part.split()[-1] for part in read_partitions if not isinstance(part.strip()[-1], int)])

        read_diskstats = self.observer_data[index]['f_diskstats']
        disk_stats = [self.parse_diskstats(line) for line in read_diskstats]
        disk_stats = {stat['dev']: stat for stat in disk_stats if stat['dev'] in partitions}

        return disk_stats


if __name__ == '__main__':
    o = Observer(sleep=1, count=5)
    #o.diskstats()
    o.vmstats()
    #print_output()