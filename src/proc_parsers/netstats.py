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