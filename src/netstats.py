class NetStats:
    def __init__(self, observer):
        self.observer = observer
        self.my_metric_key = "netstats"
        self.observer.proc_instances[self.my_metric_key] = self
        self.observer.calculated_values[self.my_metric_key] = dict()
        self.observer.raw_values[self.my_metric_key] = dict()

    def calculate_values(self, index):
        self.observer.raw_values[self.my_metric_key][index] = {"netstats": {"test": 10}}

    def get_netstats(self, index):
        netstats = dict()
        netstats["eth0"] = {"metric", "metric_value"}
        self.observer.raw_values[self.my_metric_key][index] = netstats