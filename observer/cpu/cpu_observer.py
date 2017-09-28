from cpu.analyze import AnalyzeCPUStats
from cpu.load import LoadCPUStats
from cpu.check import CheckCPUStats


class CPUObserver:
    def __init__(self, observer):
        self.observer = observer
        self.metric_key = "cpu"
        self.observer.observer_instances[self.metric_key] = dict()
        self.analyze = AnalyzeCPUStats(observer, self.metric_key)
        self.parse = LoadCPUStats(observer, self.metric_key)
        self.check = CheckCPUStats(observer, self.metric_key)
