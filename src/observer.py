import json
import time


class Observer:
    def __init__(self, sleep, count, round_precision=2, path_to_json="conf/alerts.json"):
        self.sleep = sleep
        self.count = count
        self.r_prec = round_precision
        self.file_content = dict()
        self.raw_values = dict()
        self.proc_file_dictionary = [
            "/proc/diskstats",
            "/proc/partitions",
            "/proc/stat",
            "/proc/loadavg",
            "/proc/vmstat",
            "/proc/meminfo",
            "/proc/mounts"
        ]

        self.file_content = self.load_file_data()
        self.path_to_json = path_to_json
        self.alert_data = self.json_reader()
        self.system_uptime_seconds = self.get_system_uptime()
        self.calculated_values = dict()

        self.proc_instances = dict()
        self.diskstats = DiskStats(self)
        self.vmstats = VMStats(self)
        self.procceses = Processes(self)
        self.netstats = NetStats(self)
        self.cpustats = CPUStats(self)

    def run_analyzer(self):
        for index in range(1, self.count):
            for metric_key in self.proc_instances:
                self.proc_instances[metric_key].calculate_values(index)

        for metric_key in self.proc_instances:
            self.load_initial_values(metric_key)

        for index in range(2, self.count):
            for metric_key in self.proc_instances:
                self.calculate_values(metric_key, index)

        for index in range(1, self.count-1):
            for metric_key in self.proc_instances:
                self.caclulate_diffs(index, metric_key)

        for metric_key in self.proc_instances:
            self.calculate_sums(metric_key)
            self.calculate_averages(metric_key)

        self.display_analysis()

    def load_initial_values(self, metric_key):
        for device, device_stats in self.raw_values[metric_key][1].items():
            if device not in self.calculated_values[metric_key]:
                self.calculated_values[metric_key][device] = {
                    stat_name: {
                        "Values": [stat_value],
                        "Start": stat_value,
                        "End": stat_value,
                        "Sum": stat_value,
                        "Min": stat_value,
                        "Max": stat_value,
                        "Avg": stat_value,
                        "DiffValues": [],
                        "DiffSum": round(self.raw_values[metric_key][2][device][stat_name] - stat_value, self.r_prec),
                        "DiffMin": round(self.raw_values[metric_key][2][device][stat_name] - stat_value, self.r_prec),
                        "DiffMax": round(self.raw_values[metric_key][2][device][stat_name] - stat_value, self.r_prec)
                    } for stat_name, stat_value in device_stats.copy().items()
                }

    def calculate_values(self, metric_key, index):
        for device, device_stats in self.raw_values[metric_key][index].items():
            for stat_name, stat_value in device_stats.items():
                self.calculated_values[metric_key][device][stat_name]["Values"].append(stat_value)
                self.calculated_values[metric_key][device][stat_name]["End"] = stat_value
                self.min_max_generator(metric_key, device, stat_name, stat_value, "Min", "Max")

    def caclulate_diffs(self, index, metric_key):
        for device, device_stats in self.raw_values[metric_key][index].items():
            for stat_name, stat_value in device_stats.items():
                next_stat_value = self.raw_values[metric_key][index+1][device][stat_name]
                stat_diff = round(next_stat_value - stat_value, self.r_prec)
                self.calculated_values[metric_key][device][stat_name]["DiffValues"].append(stat_diff)
                self.min_max_generator(metric_key, device, stat_name, stat_diff, "DiffMin", "DiffMax")

    def calculate_averages(self, metric_key):
        for device in self.calculated_values[metric_key]:
            for stat_name, stat_values in self.calculated_values[metric_key][device].items():
                self.calculated_values[metric_key][device][stat_name]["Avg"] = \
                    round(float(stat_values["Sum"]) / (self.count-1), self.r_prec)
                self.calculated_values[metric_key][device][stat_name]["DiffAvg"] = \
                    round(float(stat_values["DiffSum"]) / (self.count-1), self.r_prec)

    def calculate_sums(self, metric_key):
        for device in self.calculated_values[metric_key]:
            for stat_name, stat_values in self.calculated_values[metric_key][device].items():
                self.calculated_values[metric_key][device][stat_name]["Sum"] = round(
                    sum(self.calculated_values[metric_key][device][stat_name]["Values"]), self.r_prec)
                self.calculated_values[metric_key][device][stat_name]["DiffSum"] = round(
                    sum(self.calculated_values[metric_key][device][stat_name]["DiffValues"]), self.r_prec)

    def calculate_avg_diff(self, metric_key):
        for device in self.calculated_values[metric_key]:
            for stat_name, stat_values in self.calculated_values[metric_key][device].items():
                self.calculated_values[metric_key][device][stat_name]["DiffSum"] = round(
                    sum(self.calculated_values[metric_key][device][stat_name]["Values"]), self.r_prec)
                self.calculated_values[metric_key][device][stat_name]["DiffAvg"] = \
                    round(float(stat_values["DiffSum"]) / (self.count-1), self.r_prec)

    def display_analysis(self):
        for metric_name, metric_values in self.calculated_values.items():
            for device, device_stats in metric_values.items():
                for stat_name in device_stats:
                    print(metric_name, device, {stat_name: {
                            k: v for k, v in self.calculated_values[metric_name][device][stat_name].items()
                    }})

    def min_max_generator(self, metric_key, device, stat_name, stat_value, key_min, key_max):
        print("Comparing [%s] <> [%s]" % (
            self.calculated_values[metric_key][device][stat_name][key_min],
            stat_value
        ))

        if float(self.calculated_values[metric_key][device][stat_name][key_min]) > float(stat_value):
            print("New [%s]" % key_min)
            self.calculated_values[metric_key][device][stat_name][key_min] = round(float(stat_value), self.r_prec)

        if float(self.calculated_values[metric_key][device][stat_name][key_max]) < float(stat_value):
            print("New [%s]" % key_max)
            self.calculated_values[metric_key][device][stat_name][key_max] = round(float(stat_value), self.r_prec)

    def file_reader(self, index):
        print("Loading proc statistics [index: %s]" % index)
        self.file_content[index]['ts'] = time.time()
        for file_name in self.proc_file_dictionary:
            self.file_content[index][file_name] = self.get_file_content(file_name)

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

    def load_file_data(self):
        assert self.count >= 2, 'Count must be >= 2'

        print("Will generate [%s] metrics with [%s] seconds time interval" % (self.count, self.sleep))

        for index in range(1, self.count):
            self.file_content[index] = dict()
            self.file_reader(index)
            time.sleep(self.sleep)

        self.file_content[self.count] = dict()
        self.file_reader(self.count)

        return self.file_content

    @staticmethod
    def get_system_uptime():
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        return uptime_seconds

    def json_reader(self):
        return json.loads(open(self.path_to_json).read())

    def get_file_content(self, file_name):
        with open(file_name) as f:
            return f.readlines()

if __name__ == '__main__':
    from cpustats import CPUStats
    from diskstats import DiskStats
    from netstats import NetStats
    from vmstats import VMStats
    from processes import Processes

    start = time.time()
    _sleep = 0.5
    _count = 5
    o = Observer(sleep=_sleep, count=_count)
    o.run_analyzer()
    print("Finished calculations in [%s] seconds" % (time.time() - start - _sleep*_count))
