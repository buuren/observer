import os
import time
import json


class Processes:
    def __init__(self, observer):
        self.observer = observer
        self.my_metric_key = "processes"
        self.observer.calculated_values[self.my_metric_key] = dict()
        self.observer.raw_results[self.my_metric_key] = dict()


class CPUStats:
    def __init__(self, observer):
        self.observer = observer
        self.my_metric_key = "cpustats"
        self.observer.calculated_values[self.my_metric_key] = dict()
        self.observer.raw_results[self.my_metric_key] = dict()

    def get_cpustats(self, index):
        cpu_stats = dict()
        cpu_last = self.cpu_io_counters(index)
        cpu_curr = self.cpu_io_counters(index + 1)

        for device in cpu_curr.keys():
            calculations = {
                k: round(v, 2) for k, v in self.cpustats_calc(
                    last=cpu_last[device],
                    curr=cpu_curr[device]
                ).items()
            }
            cpu_stats[device] = calculations

        self.observer.raw_results[self.my_metric_key][index] = cpu_stats

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

    def cpu_io_counters(self, index):
        read_cpu_stats = self.observer.file_content[index]['/proc/stat'][:os.cpu_count()+1]
        cpu_stats = [self.parse_cpustats(line) for line in read_cpu_stats]
        cpu_stats = {stat['dev']: stat for stat in cpu_stats}
        return cpu_stats

    def get_deltams(self, index):
        cpu_last = self.cpu_io_counters(index)['cpu']
        cpu_curr = self.cpu_io_counters(index + 1)['cpu']

        curr_cpu_load = int(cpu_curr['user']) + int(cpu_curr['system']) + \
            int(cpu_curr['idle']) + int(cpu_curr['iowait'])

        last_cpu_load = int(cpu_last['user']) + int(cpu_last['system']) + \
            int(cpu_last['idle']) + int(cpu_last['iowait'])

        hz = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
        deltams = 1000 * (int(curr_cpu_load) - int(last_cpu_load)) / os.cpu_count() / hz
        return deltams


class VMStats:
    def __init__(self, observer):
        self.observer = observer
        self.my_metric_key = "vmstats"
        self.observer.calculated_values[self.my_metric_key] = dict()
        self.observer.raw_results[self.my_metric_key] = dict()

    def get_vmstats(self, index):
        vmstats = self.vmstat_counters(index)
        self.observer.raw_results[self.my_metric_key][index] = vmstats

    @staticmethod
    def parse_loadavg(line):
        load_one_min, load_five_min, load_fifteen_min, curr_proc, last_proc_id = line.split()
        proc_scheduled = curr_proc.split('/')[0]
        entities_total = curr_proc.split('/')[1]
        del line, curr_proc, last_proc_id
        d = {k: float(v) for k, v in locals().items()}
        return d

    def vmstat_counters(self, index):
        read_loadvg = self.observer.file_content[index]['/proc/loadavg'][0]
        read_vmstat = self.observer.file_content[index]['/proc/vmstat']

        vmstats = dict()
        vmstats['loadavg'] = self.parse_loadavg(read_loadvg)
        vmstats['vmstat'] = {stat.split()[0]: int(stat.split()[1]) for stat in read_vmstat}
        return vmstats


class DiskStats:
    def __init__(self, observer):
        self.sector_size = 512
        self.observer = observer
        self.my_metric_key = 'diskstats'
        self.observer.calculated_values[self.my_metric_key] = dict()
        self.observer.raw_results[self.my_metric_key] = dict()

    def analyze_diskstats(self):
        my_alert_data = self.observer.alert_data[self.my_metric_key]

        for alert_metric, alert_value in my_alert_data.items():
            warning_value = int(alert_value['warning'])
            critical_value = int(alert_value['critical'])

            for device, device_stats in self.observer.average_values[self.my_metric_key].items():
                actual_value = int(device_stats[alert_metric])
                self.observer.compare_values(
                    metrics=locals()
                )

    def get_diskstats(self, index, deltams):
        disk_stats = dict()
        disk_last = self.disk_io_counters(index)
        disk_curr = self.disk_io_counters(index + 1)

        for device in disk_curr.keys():
            calculations = {
                k: round(v, 2) for k, v in self.calc(
                    last=disk_last[device],
                    curr=disk_curr[device],
                    ts_delta=self.observer.get_ts_delta(index),
                    deltams=deltams
                ).items()
            }
            disk_stats[device] = calculations

        self.observer.raw_results[self.my_metric_key][index] = disk_stats

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

        disk_stats['f_blocks'] = last['f_blocks']
        disk_stats['f_bsize'] = last['f_bsize']
        disk_stats['f_frsize'] = last['f_frsize']
        disk_stats['f_bfree'] = last['f_bfree']
        disk_stats['f_bavail'] = last['f_bavail']
        disk_stats['f_files'] = last['f_files']
        disk_stats['f_ffree'] = last['f_ffree']
        disk_stats['f_favail'] = last['f_favail']
        disk_stats['f_flag'] = last['f_flag']
        disk_stats['f_namemax'] = last['f_namemax']

        return disk_stats

    def disk_io_counters(self, index):
        read_partitions = self.observer.file_content[index]['/proc/partitions'][2:]
        partitions = set([part.split()[-1] for part in read_partitions if not isinstance(part.strip()[-1], int)])

        read_diskstats = self.observer.file_content[index]['/proc/diskstats']
        disk_stats = [self.parse_diskstats(line) for line in read_diskstats]
        disk_stats = {stat['dev']: stat for stat in disk_stats if stat['dev'] in partitions}

        return disk_stats

    @staticmethod
    def parse_diskstats(line):
        major, minor, dev, r_ios, r_merges, r_sec, r_ticks, w_ios, w_merges, \
            w_sec, w_ticks, ios_pgr, tot_ticks, rq_ticks = line.split()

        disk_usage_stats = os.statvfs("/dev/%s" % dev)
        f_bsize, f_frsize, f_blocks, f_bfree, f_bavail, f_files, f_ffree, f_favail, f_flag, f_namemax = [
            x for x in tuple(disk_usage_stats)]

        del line, disk_usage_stats
        d = {k: v for k, v in locals().items()}

        return d


class NetStats:
    def __init__(self, observer):
        self.observer = observer
        self.my_metric_key = "netstats"
        self.observer.calculated_values[self.my_metric_key] = dict()
        self.observer.raw_results[self.my_metric_key] = dict()

    def get_netstats(self, index):
        netstats = dict()
        netstats["eth0"] = {"metric", "metric_value"}
        self.observer.raw_results[self.my_metric_key][index] = netstats


class Observer:
    def __init__(self, sleep, count, path_to_json="conf/alerts.json"):
        self.sleep = sleep
        self.count = count
        self.file_content = dict()
        self.raw_results = dict()
        self.proc_file_dictionary = {
            "/proc/diskstats": "/proc/diskstats",
            "/proc/partitions": "/proc/partitions",
            "/proc/stat": "/proc/stat",
            "/proc/loadavg": "/proc/loadavg",
            "/proc/vmstat": "/proc/vmstat"

        }
        self.file_content = self.load_file_data(sleep, count)
        self.path_to_json = path_to_json
        self.alert_data = self.json_reader()
        self.system_uptime_seconds = self.get_system_uptime()
        self.calculated_values = dict()

        self.diskstats = DiskStats(self)
        self.vmstats = VMStats(self)
        self.procceses = Processes(self)
        self.netstats = NetStats(self)
        self.cpustats = CPUStats(self)

    def run_analyzer(self):
        self.generate_raw_stats()

        for index in range(1, self.count):
            self.generate_totals(self.diskstats.my_metric_key, index)
            self.generate_totals(self.cpustats.my_metric_key, index)
            self.generate_totals(self.vmstats.my_metric_key, index)

        self.calculate_averages(self.diskstats.my_metric_key)
        self.calculate_averages(self.cpustats.my_metric_key)
        self.calculate_averages(self.vmstats.my_metric_key)

        self.calculate_deltas(self.diskstats.my_metric_key)
        self.calculate_deltas(self.cpustats.my_metric_key)
        self.calculate_deltas(self.vmstats.my_metric_key)

        self.display_analysis()

    def generate_raw_stats(self):
        for index in range(1, self.count):
            self.diskstats.get_diskstats(index, self.cpustats.get_deltams(index)),
            self.cpustats.get_cpustats(index)
            self.vmstats.get_vmstats(index)

    def generate_totals(self, my_metric_key, index):
        indexed_raw_metric_results = self.raw_results[my_metric_key][index]

        for device, device_stats in indexed_raw_metric_results.items():
            for stat_name, stat_value in device_stats.items():
                if device not in self.calculated_values[my_metric_key]:
                    self.calculated_values[my_metric_key][device] = {stat_name: {
                        "Sum": stat_value, "Min": 0.0, "Max": 0.0, "Avg": 0.0, "Delta": 0.0
                        } for stat_name, stat_value in device_stats.copy().items()
                    }
                    break

                self.calculated_values[my_metric_key][device][stat_name]["Sum"] = \
                    round((self.calculated_values[my_metric_key][device][stat_name]["Sum"] + float(stat_value)), 2)
                self.min_max_generator(my_metric_key, device, stat_name, stat_value)

    def calculate_averages(self, my_metric_key):
        for device in self.calculated_values[my_metric_key]:
            for stat_name, stat_values in self.calculated_values[my_metric_key][device].items():
                self.calculated_values[my_metric_key][device][stat_name]["Avg"] = \
                    float(stat_values["Sum"]) / (self.count - 1)

    def calculate_deltas(self, my_metric_key):
        for device in self.calculated_values[my_metric_key]:
            for stat_name, stat_values in self.calculated_values[my_metric_key][device].items():
                first_value = self.raw_results[my_metric_key][1][device][stat_name]
                end_value = self.raw_results[my_metric_key][self.count - 1][device][stat_name]

                self.calculated_values[my_metric_key][device][stat_name]["Start"] = first_value
                self.calculated_values[my_metric_key][device][stat_name]["End"] = end_value
                self.calculated_values[my_metric_key][device][stat_name]["Delta"] = round((end_value - first_value), 2)

    def display_analysis(self):
        for metric_name, metric_values in self.calculated_values.items():
            for device, device_stats in metric_values.items():
                for stat_name in device_stats:
                    print(device, {stat_name: {
                        k: v for k, v in self.calculated_values[metric_name][device][stat_name].items()}}
                    )

    def min_max_generator(self, my_metric_key, device, stat_name, stat_value):
        if float(self.calculated_values[my_metric_key][device][stat_name]["Min"]) > float(stat_value):
            self.calculated_values[my_metric_key][device][stat_name]["Min"] = round(float(stat_value), 2)

        if float(self.calculated_values[my_metric_key][device][stat_name]["Max"]) < float(stat_value):
            self.calculated_values[my_metric_key][device][stat_name]["Max"] = round(float(stat_value), 2)

    def file_reader(self, index):
        print("Generating metrics with index [%s]" % index)
        for proc, file_name in self.proc_file_dictionary.items():
            with open(file_name) as f:
                self.file_content[index][proc] = f.readlines()
                self.file_content[index]['ts'] = os.stat(f.name).st_mtime

    def get_ts_delta(self, index):
        return self.file_content[index+1]["ts"] - self.file_content[index]["ts"]

    def compare_values(self, metrics):
        if metrics['actual_value'] >= metrics['critical_value']:
            print("Device [%s]: [%s] has reached critical value [%s]" % (
                metrics['device'], metrics['alert_metric'], metrics['actual_value']
            ))
            status = "CRITICAL"
        elif metrics['actual_value'] >= metrics['warning_value']:
            print("Device [%s]: [%s] has reached warning value [%s]" % (
                metrics['device'], metrics['alert_metric'], metrics['actual_value']
            ))
            status = "WARNING"
        else:
            status = "OK"

        return status

    def load_file_data(self, sleep, count):
        assert count >= 2, 'Count must be equal or greater 2'

        print("Will generate [%s] metrics with [%s] seconds time interval" % (count, sleep))
        for index in range(1, count):
            self.file_content[index] = dict()
            self.file_reader(index)
            time.sleep(sleep)

        self.file_content[count] = dict()
        self.file_reader(count)

        return self.file_content

    @staticmethod
    def get_system_uptime():
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])

        return uptime_seconds

    def json_reader(self):
        return json.loads(open(self.path_to_json).read())

if __name__ == '__main__':
    start = time.time()
    _sleep = 1
    _count = 5
    o = Observer(sleep=_sleep, count=_count)
    o.run_analyzer()
    print("Finished calculations in [%s] seconds" % (time.time() - start - (_count - 1)))
