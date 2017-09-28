class NetStats:
    def __init__(self, observer):
        self.observer = observer
        self.metric_key = "netstats"
        self.file_list = ["packet"]
        self.keep_filenames = dict()
        self.observer.proc_instances[self.metric_key] = self
        self.observer.calculated_values[self.metric_key] = dict()
        self.observer.raw_values[self.metric_key] = dict()

    def calculate_values(self, index):
        self.observer.raw_values[self.metric_key][index] = {"netstats": {"test": 10}}

    def get_netstats(self, index):
        netstats = dict()
        netstats["eth0"] = {"metric", "metric_value"}
        self.observer.raw_values[self.metric_key][index] = netstats

    def return_proc_location(self, index):
        list_of_filenames = ['/proc/net/%s' % filename for filename in self.file_list]
        self.keep_filenames[index] = list_of_filenames
        return list_of_filenames
