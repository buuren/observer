import os


class DiskStats:
    def __init__(self, observer):
        self.sector_size = 512
        self.observer = observer
        self.my_metric_key = 'diskstats'
        self.observer.proc_instances[self.my_metric_key] = self
        self.observer.calculated_values[self.my_metric_key] = dict()
        self.observer.raw_values[self.my_metric_key] = dict()

    def calculate_values(self, index):
        disk_stats = dict()
        disk_last = self.generate_counters(index)
        disk_curr = self.generate_counters(index+1)

        for device in disk_curr.keys():
            calculations = {
                k: round(v, self.observer.r_prec) for k, v in self.calc_disk_stats(
                    last=disk_last[device],
                    curr=disk_curr[device],
                    ts_delta=self.observer.get_ts_delta(index),
                    deltams=self.observer.cpustats.get_deltams(index),
                    r_prec=self.observer.r_prec
                ).items()
            }
            disk_stats[device] = calculations

        self.observer.raw_values[self.my_metric_key][index] = disk_stats

    def generate_counters(self, index):
        disk_stats = self.parse_diskstats(index)
        disk_stats = self.parse_partitions(index, disk_stats)
        disk_stats = self.parse_mounts(index, disk_stats)
        return disk_stats

    def calc_disk_stats(self, last, curr, ts_delta, deltams, r_prec):
        disk_stats = {}

        def calc_iops():

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

        def calc_storage_stats():
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

            disk_stats['total_gb'] = round(
                (float(last['f_blocks']) * float(last['f_frsize'])) / 1073741824, r_prec)
            disk_stats['available_gb'] = round(
                (float(last['f_bavail']) * float(last['f_frsize'])) / 1073741824, r_prec)
            disk_stats['free_gb'] = round(
                (float(last['f_bfree']) * float(last['f_frsize'])) / 1073741824, r_prec)
            disk_stats['used_gb'] = round(
                float(disk_stats['total_gb']) - float(disk_stats['available_gb']), r_prec)
            disk_stats['%used'] = round(
                (float(disk_stats['used_gb']) / float(disk_stats['total_gb'])) * 100, r_prec) \
                if float(disk_stats['total_gb']) > 0 else 0

        if 'r_merges' in last.keys():
            calc_iops()

        if 'f_blocks' in last.keys():
            calc_storage_stats()

        return disk_stats

    def parse_diskstats(self, index):
        return {
            line.split()[2]: {
                "major": line.split()[0],
                "minor": line.split()[1],
                "r_ios": line.split()[3],
                "r_merges":  line.split()[4],
                "r_sec": line.split()[5],
                "r_ticks": line.split()[6],
                "w_ios": line.split()[7],
                "w_merges": line.split()[8],
                "w_sec": line.split()[9],
                "w_ticks": line.split()[10],
                "ios_pgr": line.split()[11],
                "tot_ticks": line.split()[12],
                "rq_ticks": line.split()[13],
            } for line in self.observer.file_content[index]['/proc/diskstats']
        }

    def parse_stavs(self, index, disk_device):
        f_bsize, f_frsize, f_blocks, f_bfree, f_bavail, f_files, f_ffree, f_favail, f_flag, f_namemax = [
            x for x in tuple(os.statvfs(disk_device))
        ]

        del disk_device, index, self
        d = {k: v for k, v in locals().items()}
        return d

    def parse_partitions(self, index, read_diskstats):
        d = {part.split()[-1]: {
                "#blocks": part.split()[-2],
                "minor": part.split()[-3],
                "major": part.split()[-4]
            } for part in self.observer.file_content[index]['/proc/partitions'][2:]
            if not isinstance(part.strip()[-1], int)
        }

        for key in read_diskstats.keys():
            read_diskstats[key] = {**read_diskstats[key], **(d[key])}

        return read_diskstats

    def parse_mounts(self, index, read_partitions):
        d = {
            device_data.split()[0]: {
                "mount_point": device_data.split()[1],
                "fs_type": device_data.split()[2],
                "mount_opts": ' '.join(device_data.split()[3:])
            } for device_data in self.observer.file_content[index]['/proc/mounts']
        }

        for key in d.keys():
            statvfs_values = self.parse_stavs(index, d[key]['mount_point'])
            partition_name = key.split('/dev/')[-1]

            if partition_name in read_partitions.keys():
                read_partitions[partition_name] = {
                    **read_partitions[partition_name],
                    **(d[key]),
                    **statvfs_values
                }
            else:
                read_partitions[key] = {
                    **(d[key]),
                    **statvfs_values
                }

        return read_partitions
