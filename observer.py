import os
import time
import json
import resource


class Processes:
    def __init__(self, observer):
        self.observer = observer


class CPUStats:
    def __init__(self, observer):
        self.sector_size = 1
        self.observer = observer

    def get_cpustats(self, index):
        cpu_stats = dict()
        cpu_stats['cpustats'] = dict()

        cpu_last = self.cpu_io_counters(index)
        cpu_curr = self.cpu_io_counters(index + 1)

        for dev in cpu_curr.keys():
            cpu_stats['cpustats'][dev] = {
                k: round(v, 2) for k, v in self.cpustats_calc(
                    last=cpu_last[dev],
                    curr=cpu_curr[dev]
                ).items()
            }
        return cpu_stats

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

    def get_vmstats(self, index):
        vmstats = dict()
        vmstats['vmstats'] = dict()
        vmstats['vmstats'] = self.vmstat_counters(index)
        return vmstats

    @staticmethod
    def parse_loadavg(line):
        one_min, five_min, fifteen_min, curr_proc, last_proc_id = line.split()
        proc_scheduled = curr_proc.split('/')[0]
        entities_total = curr_proc.split('/')[1]
        del line, curr_proc
        d = {k: v for k, v in locals().items()}
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
        super()
        self.sector_size = 512
        self.observer = observer
        self.my_metric_key = 'diskstats'

    def analyze_diskstats(self, diskstat_results):
        my_alert_data = self.observer.alert_data[self.my_metric_key]
        for device, device_stats in diskstat_results.items():
            for alert_metric, alert_value in my_alert_data.items():
                warning_value = int(alert_value['warning'])
                critical_value = int(alert_value['critical'])
                actual_value = int(device_stats[alert_metric])

                self.observer.compare_values(
                    metrics=locals()
                )

    def get_diskstats(self, index):
        disk_stats = dict()
        disk_stats[self.my_metric_key] = dict()

        disk_last = self.disk_io_counters(index)
        disk_curr = self.disk_io_counters(index + 1)

        cpu_runner = CPUStats(self.observer)
        deltams = cpu_runner.get_deltams(index)

        for device in disk_curr.keys():
            calculations = {
                k: round(v, 2) for k, v in self.calc(
                    last=disk_last[device],
                    curr=disk_curr[device],
                    ts_delta=self.observer.get_ts_delta(index),
                    deltams=deltams
                ).items()
            }
            disk_stats[self.my_metric_key][device] = calculations

        return disk_stats

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

    @staticmethod
    def parse_diskstats(line):
        major, minor, dev, r_ios, r_merges, r_sec, r_ticks, w_ios, w_merges, \
            w_sec, w_ticks, ios_pgr, tot_ticks, rq_ticks = line.split()

        del line
        d = {k: v for k, v in locals().items()}
        return d

    def disk_io_counters(self, index):
        read_partitions = self.observer.file_content[index]['/proc/partitions'][2:]
        partitions = set([part.split()[-1] for part in read_partitions if not isinstance(part.strip()[-1], int)])

        read_diskstats = self.observer.file_content[index]['/proc/diskstats']
        disk_stats = [self.parse_diskstats(line) for line in read_diskstats]
        disk_stats = {stat['dev']: stat for stat in disk_stats if stat['dev'] in partitions}

        return disk_stats


class NetStats:
    def __init__(self, observer):
        self.observer = observer

    def get_netstats(self, index):
        netstats = dict()
        netstats['netstats'] = dict()
        netstats['netstats'] = {"eth0": {"metric", "metric_value"}}
        return netstats


class Observer:
    def __init__(self, sleep, count, path_to_json="conf/alerts.json"):
        self.sleep = sleep
        self.count = count
        self.path_to_json = path_to_json
        self.file_content = dict()
        self.data = dict()
        self.proc_file_dictionary = {
            "/proc/diskstats": "/proc/diskstats",
            "/proc/partitions": "/proc/partitions",
            "/proc/stat": "/proc/stat",
            "/proc/loadavg": "/proc/loadavg",
            "/proc/vmstat": "/proc/vmstat"
        }

        self.file_content = self.data_generator(sleep, count)
        self.alert_data = self.json_reader()

        self.diskstats = DiskStats(self)
        self.vmstats = VMStats(self)
        self.procceses = Processes(self)
        self.netstats = NetStats(self)
        self.cpustats = CPUStats(self)

    def generate_calculations(self):
        calculated_results = {}

        for index in range(1, self.count):
            calculated_results[index] = {
                **self.diskstats.get_diskstats(index),
                **self.cpustats.get_cpustats(index),
                **self.vmstats.get_vmstats(index),
                **self.netstats.get_netstats(index)
            }

        # self.display_calculations(calculated_results)
        self.run_analyzer(calculated_results)

    def display_calculations(self, calculated_results):
        for index in calculated_results.keys():
            ts_delta = self.get_ts_delta(index)
            last_ts = self.file_content[index]['ts']
            curr_ts = self.file_content[index+1]['ts']
            print("Generation completed - displaying results...")
            print("")

            start_date = time.strftime("%Z - %Y/%m/%d, %H:%M:%S", time.localtime(last_ts))
            end_date = time.strftime("%Z - %Y/%m/%d, %H:%M:%S", time.localtime(curr_ts))
            rounded_ts_delta = round(ts_delta, 4)

            for statistics in calculated_results[index].keys():
                print("[%s-%s] Statistics from [%s] to [%s] (Delta: %s ms)" % (
                    statistics, index, start_date, end_date, rounded_ts_delta
                ))
                print("----------------------------------------------------------------------------------------------")
                for stat_name, stat_values in calculated_results[index][statistics].items():
                    print(stat_name, stat_values)
                print("")

    def run_analyzer(self, calculated_results):
        for index in range(1, self.count):
            self.diskstats.analyze_diskstats(
                diskstat_results=calculated_results[index][self.diskstats.my_metric_key]
            )

    def data_generator(self, sleep, count):
        assert count >= 2, 'Count must be equal or greater 2'

        print("Will generate [%s] metrics with [%s] seconds time interval" % (count, sleep))
        for index in range(1, count):
            self.file_content[index] = dict()
            self.file_reader(index)
            time.sleep(sleep)

        self.file_content[count] = dict()
        self.file_reader(count)

        return self.file_content

    def file_reader(self, index):
        print("Generating metrics with index [%s]" % index)
        for proc, file_name in self.proc_file_dictionary.items():
            with open(file_name) as f:
                self.file_content[index][proc] = f.readlines()
                self.file_content[index]['ts'] = os.stat(f.name).st_mtime

    def get_ts_delta(self, index):
        return self.file_content[index+1]["ts"] - self.file_content[index]["ts"]

    def json_reader(self):
        return json.loads(open(self.path_to_json).read())

    @staticmethod
    def compare_values(metrics):

        # print('Device [%s] - Metric [%s] - Warning value [%s] - Critical value [%s] - Actual [%s]' % (
        #    device,
        #    alert_metric,
        #    warning_value,
        #    critical_value,
        #    actual_value
        # ))

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

if __name__ == '__main__':
    o = Observer(sleep=1, count=5)
    o.generate_calculations()
