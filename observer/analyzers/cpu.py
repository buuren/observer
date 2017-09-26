from parsers.cpu import CPUStats


class AnalyzeCPUStats(CPUStats):
    def __init__(self, observer):
        self.cpustats = CPUStats.__init__(self, observer)

    def execute_analysis(self):
        self.check_uptime()

    def check_uptime(self):
        print(self.observer.calculate_values(self.metric_key))
