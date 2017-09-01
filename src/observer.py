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
        for index in range(1, self.count+1):
            for metric_key in self.proc_instances:
                self.proc_instances[metric_key].calculate_values(index)
                self.calculate_global_values(metric_key, index)

        for index in range(1, self.count+1):
            for metric_key in self.proc_instances:
                self.calculate_averages(metric_key)

        self.display_analysis()

    def calculate_global_values(self, my_metric_key, index):
        indexed_raw_metric_results = self.raw_values[my_metric_key][index]

        for device, device_stats in indexed_raw_metric_results.items():
            for stat_name, stat_value in device_stats.items():
                if device not in self.calculated_values[my_metric_key]:
                    self.calculated_values[my_metric_key][device] = {
                        stat_name: {
                            "Sum": stat_value,
                            "Min": stat_value,
                            "Max": stat_value,
                            "Avg": stat_value
                        } for stat_name, stat_value in device_stats.copy().items()
                    }
                    break

                self.calculated_values[my_metric_key][device][stat_name]["Sum"] = round(
                    (self.calculated_values[my_metric_key][device][stat_name]["Sum"] + float(stat_value)), self.r_prec
                )
                self.min_max_generator(my_metric_key, device, stat_name, stat_value)

    def calculate_averages(self, metric_key):
        for device in self.calculated_values[metric_key]:
            for stat_name, stat_values in self.calculated_values[metric_key][device].items():
                self.calculated_values[metric_key][device][stat_name]["Avg"] = \
                    round(float(stat_values["Sum"]) / self.count, self.r_prec)

                first_value = self.raw_values[metric_key][1][device][stat_name]
                end_value = self.raw_values[metric_key][self.count][device][stat_name]

                self.calculated_values[metric_key][device][stat_name]["Start"] = first_value
                self.calculated_values[metric_key][device][stat_name]["End"] = end_value
                self.calculated_values[metric_key][device][stat_name]["Delta"] = round(
                    (end_value - first_value), self.r_prec
                )

    def display_analysis(self):
        for metric_name, metric_values in self.calculated_values.items():
            for device, device_stats in metric_values.items():
                for stat_name in device_stats:
                    print(metric_name, device, {
                        stat_name: {
                            k: v for k, v in self.calculated_values[metric_name][device][stat_name].items()
                        }
                    })

    def min_max_generator(self, my_metric_key, device, stat_name, stat_value):
        if float(self.calculated_values[my_metric_key][device][stat_name]["Min"]) > float(stat_value):
            self.calculated_values[my_metric_key][device][stat_name]["Min"] = round(float(stat_value), self.r_prec)

        if float(self.calculated_values[my_metric_key][device][stat_name]["Max"]) < float(stat_value):
            self.calculated_values[my_metric_key][device][stat_name]["Max"] = round(float(stat_value), self.r_prec)

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
    _sleep = 2
    _count = 2
    o = Observer(sleep=_sleep, count=_count)
    o.run_analyzer()
    print("Finished calculations in [%s] seconds" % (time.time() - start - _sleep))
