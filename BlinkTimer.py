import time
import asyncio
from PyQt5.QtCore import *

RECENT_BLINKS_DURATION = 60


class BlinkTimer:
    def __init__(self, app, thread):
        self.eye_open_time = time.time()
        self.notification_time = 0
        self.start_time = time.time()
        self.waiting_blink = False
        self.blink_entries_recent = []
        self.app = app
        self.thread = thread
        self.on_break = False
        self.app.start_break_signal.connect(self.on_break_start)
        self.app.finish_break_signal.connect(self.on_break_finish)

        self.on_blink_finish()

    def on_break_start(self):
        self.waiting_blink = False
        self.on_break = True
        self.app.stop_blink_reminder_signal.emit()

    def on_break_finish(self):
        self.start_time = time.time()
        self.blink_entries_recent = []
        self.on_break = False
        self.on_blink_finish()

    def tick(self, frame_data):
        if self.on_break:
            return

        self.handle_frame_events(frame_data)
        self.handle_eyes_open_timeout(frame_data)
        self.update_blink_rate()

    def handle_frame_events(self, frame_data):
        if frame_data.is_blink_start:
            self.on_blink_start()
        if frame_data.is_blink_finish:
            self.on_blink_finish()
        if frame_data.is_afk_start:
            self.app.stop_blink_reminder_signal.emit()
        if frame_data.is_afk_finish:
            self.on_blink_finish()

    def handle_eyes_open_timeout(self, frame_data):
        eyes_open_timeout = time.time() >= self.notification_time
        if eyes_open_timeout and not self.waiting_blink and not frame_data.is_blinking and not frame_data.is_afk:
            self.waiting_blink = True
            self.app.start_blink_reminder_signal.emit()

    def update_blink_rate(self):
        len_blinks_recent = len(self.blink_entries_recent)
        if len_blinks_recent > 0 and self.blink_entries_recent[0] < time.time() - RECENT_BLINKS_DURATION:
            self.blink_entries_recent.pop(0)
        blink_rate_recent = len_blinks_recent * 60 / self.get_elapsed_time()

        self.app.update_blink_rate_signal.emit(blink_rate_recent, blink_rate_recent)

    def on_blink_start(self):
        self.blink_entries_recent.append(time.time())

        if self.waiting_blink:
            self.waiting_blink = False
            self.app.stop_blink_reminder_signal.emit()

    def on_blink_finish(self):
        self.eye_open_time = time.time()
        self.notification_time = self.eye_open_time + self.calculate_notification_delay()

    def calculate_notification_delay(self):
        target_blink_rate = self.thread.get_setting("target_blink_rate")

        recent_blink_count = len(self.blink_entries_recent)
        elapsed_time = self.get_elapsed_time()
        blink_reminder_rigidness = self.thread.get_setting("blink_reminder_rigidness") / 50
        projected_blink_count = target_blink_rate / 60 * (1 + blink_reminder_rigidness) * RECENT_BLINKS_DURATION
        remaining_blinks = projected_blink_count - recent_blink_count
        remaining_time = (1 + blink_reminder_rigidness) * RECENT_BLINKS_DURATION - elapsed_time
        target_rate = remaining_blinks / remaining_time
        target_rate = max(target_rate, target_blink_rate / 60 / 2, 10 / 60)
        target_rate = min(target_rate, target_blink_rate / 60 * 2, 1)

        return 1 / target_rate

    def get_elapsed_time(self):
        elapsed_time = time.time() - self.start_time
        if elapsed_time > RECENT_BLINKS_DURATION:
            elapsed_time = RECENT_BLINKS_DURATION
        return elapsed_time

        #return min(time.time() - self.start_time, RECENT_BLINKS_DURATION)