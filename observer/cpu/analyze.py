

class AnalyzeCPUStats:
    def __init__(self, observer, metric_key):
        self.observer = observer
        observer.observer_instances[metric_key]["analyze"] = self

    def execute_analysis(self):
        self.check_uptime()

    def check_uptime(self):
        pass
