from dataclasses import dataclass
from datetime import datetime


@dataclass
class StatisticsSelenium:
    START_TIME: datetime = None
    END_TIME: datetime = None
    TOTAL_REQUESTS = 0

    def add_request(self):
        self.TOTAL_REQUESTS += 1

    def start_timer(self):
        self.START_TIME = datetime.now()

    def end_timer(self):
        self.END_TIME = datetime.now()

    def get_seconds_timer(self):
        if self.START_TIME is None or self.END_TIME is None:
            return None
        return (self.END_TIME - self.START_TIME).total_seconds()

    def __repr__(self):
        return f"[StatisticsSelenium] (TOTAL_REQUESTS={self.TOTAL_REQUESTS}, START_TIME={self.START_TIME}, END_TIME={self.END_TIME}, DURATION_SECONDS={self.get_seconds_timer()})"
