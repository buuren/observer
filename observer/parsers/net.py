class NetStats:
    def __init__(self, observer):
        self.observer = observer
        self.metric_key = "netstats"

    def initiate_observer(self):
        self.observer.proc_instances[self.metric_key] = self
        self.observer.calculated_values[self.metric_key] = dict()
        self.observer.raw_values[self.metric_key] = dict()

    def calculate_values(self, index):
        self.observer.raw_values[self.metric_key][index] = {"netstats": {"test": 10}}

    def get_netstats(self, index):
        netstats = dict()
        netstats["eth0"] = {"metric", "metric_value"}
        self.observer.raw_values[self.metric_key][index] = netstats