

class CheckCPUStats:
    def __init__(self, observer, metric_key):
        self.observer = observer
        self.metric_key = metric_key
        self.observer.observer_instances["cpu"]["check"] = self

    def execute_analysis(self):
        self.check_uptime()

    def check_uptime(self):
        print(self.observer.calculate_values(self.metric_key))
