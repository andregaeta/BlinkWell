import time


class Session:
    def __init__(self, target_duration):
        self.target_duration = target_duration
        self.start_time = time.time()
        self.reminder_time = self.start_time + self.target_duration * 60
        self.finish_time = 0
        self.afk_duration = 0
        self.finished = False

        self.blink_count = 0

    def snooze(self, delay):
        self.reminder_time = time.time() + delay * 60

    def check_session_timeout(self):
        return time.time() > self.reminder_time

    def finish(self):
        self.finish_time = time.time()
        self.finished = True

    def get_final_duration(self):
        return self.finish_time - self.start_time - self.afk_duration

    def get_final_blink_rate(self):
        return self.blink_count / self.get_final_duration() * 60