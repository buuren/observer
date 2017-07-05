import time
import json
import datetime
from glob import glob
from os.path import basename, dirname
import re
from utils.binary_runner import BinaryRunner
from utils.help_functions import json_reader


class IOStatError(Exception):
    pass


class CmdError(IOStatError):
    pass


class ParseError(IOStatError):
    pass


class IOStatWrapper(BinaryRunner):
    def __init__(self, path_to_json):
        super().__init__()
        self.binary = "iostat"
        self.iostat_config_data = json_reader(path_to_json)[self.binary]
        self.binary_path = self.iostat_config_data['path']
        self.disks = []

    def get_disk_stats(self):
        disk_stats = {}
        regex = re.compile('([A-Z]+)=(?:"(.*?)")')

        run_lsblk = self.shell_run("lsblk -P -o NAME,KNAME,MODEL,UUID,SIZE,ROTA,TYPE,MOUNTPOINT,MAJ:MIN")
        get_lsblk_output = self.get_command_output(run_lsblk)

        for x in get_lsblk_output.splitlines():
            device_extra_info = dict([(k.lower(), v) for k, v in regex.findall(x)])
            disk_stats[device_extra_info['name']] = device_extra_info

        return disk_stats

    @staticmethod
    def get_disk_partitions(disk):
        if disk.startswith('.') or '/' in disk:
            raise ValueError('Invalid disk name {0}'.format(disk))
        partition_glob = '/sys/block/{0}/*/start'.format(disk)
        return [basename(dirname(p)) for p in glob(partition_glob)]

    def parse_iostat(self, data_input):
        iostat_parsed = {}
        dsi = data_input.rfind('Device:')

        if dsi == -1:
            raise ParseError('Unknown input format: %r' % data_input)

        ds = data_input[dsi:].splitlines()
        hdr = ds.pop(0).split()[1:]

        for d in ds:
            if d:
                d = d.split()
                d = [re.sub(r',', '.', element) for element in d]
                dev = d.pop(0)

                if (dev in self.disks) or not self.disks:
                    iostat_parsed[dev] = dict([(k, float(v)) for k, v in zip(hdr, d)])

        return iostat_parsed

    def iostat_data_generator(self, binary_args):
        run_iostat = self.shell_run(self.binary + binary_args)
        get_iostat_output = self.get_command_output(run_iostat)
        parsed_iostat_output = self.parse_iostat(get_iostat_output)
        return parsed_iostat_output

    def data_printer(self, data):
        disk_stats = self.get_disk_stats()

        for device_kname, device_metrics in data.items():
            if device_kname == "scd0":
                device_extra_data = disk_stats['sr0']
            else:
                device_extra_data = disk_stats[device_kname]

            extended_device_metrics = {**device_metrics, **device_extra_data}

            if device_extra_data['type'] == "lvm":
                print("[%s] is a LVM partition" % device_kname)
            elif device_extra_data['type'] == "disk":
                extended_device_metrics["partitions"] = self.get_disk_partitions(device_kname)

            for metric_name, metric_stats in extended_device_metrics.items():
                print('[Device: %s] [Metric: %s] [Value: %s]' % (device_kname, metric_name, metric_stats))

    def data_feeder(self, command_id):
        command_count = self.iostat_config_data['commands'][command_id]['count']
        command_time_interval_seconds = self.iostat_config_data['commands'][command_id]['time_interval_seconds']

        for x in range(command_count):
            # report_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            report_data = self.iostat_data_generator(
                binary_args=self.iostat_config_data['commands'][command_id]['args']
            )
            self.data_printer(report_data)

            time.sleep(command_time_interval_seconds)

if __name__ == '__main__':
    iostatRunner = IOStatWrapper('../config/centos7.json')
    #iostatRunner.get_disk_stats()
    iostatRunner.data_feeder(command_id='disk_util_extended')

    from glob import glob


    def physical_drives():
        drive_glob = '/sys/block/*/device'
        return [basename(dirname(d)) for d in glob(drive_glob)]

else:
    pass
