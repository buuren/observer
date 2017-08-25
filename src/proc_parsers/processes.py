class Processes:
    def __init__(self, observer):
        self.observer = observer
        self.my_metric_key = "processes"
        self.observer.calculated_values[self.my_metric_key] = dict()
        self.observer.raw_results[self.my_metric_key] = dict()

