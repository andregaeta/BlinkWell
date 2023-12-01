import time
from Session import Session

SESSION_DURATION = 3
BREAK_DURATION = 3
SNOOZE_DURATION = 2


class BreakTimer:
    def __init__(self, app, thread):
        self.app = app
        self.thread = thread
        self.session = Session(self.thread.get_setting("session_duration"))
        self.afk_time = 0
        self.reminding = False
        self.on_break = False
        self.break_unlocked = False
        self.break_time = 0
        self.break_reminder_enabled = True

        self.app.start_break_signal.connect(self.on_break_start)
        self.app.finish_break_signal.connect(self.on_break_stop)
        self.app.snooze_break_signal.connect(self.on_snooze)
        self.app.start_break_reminder_signal.connect(self.on_reminder_start)
        self.app.finish_break_reminder_signal.connect(self.on_reminder_finish)
        self.app.skip_break_signal.connect(self.on_skip)
        self.app.break_reminder_toggle_signal.connect(self.on_reminder_toggle)

    def tick(self, frame_data):
        self.handle_frame_events(frame_data)
        self.update_screen_time()
        self.update_break_duration()
        self.check_voluntary_break(frame_data)
        self.check_session_timeout()

    def update_screen_time(self):
        if self.session.finished:
            self.app.update_session_time_signal.emit(0)
        else:
            self.app.update_session_time_signal.emit(time.time() - self.session.start_time)

    def update_break_duration(self):
        if not self.on_break:
            return

        break_duration = time.time() - self.break_time
        break_duration_to_unlock = self.thread.get_setting("break_duration")
        self.app.update_break_duration_signal.emit(break_duration, break_duration/break_duration_to_unlock)

        if not self.break_unlocked and time.time() - self.break_time > break_duration_to_unlock:
            self.break_unlocked = True
            self.app.unlock_break_signal.emit()

    def check_voluntary_break(self, frame_data):
        if self.on_break:
            return

        if not frame_data.is_afk:
            return

        if time.time() - self.afk_time > self.thread.get_setting("break_duration"):
            if self.break_reminder_enabled:
                self.on_afk_finish()
                self.app.start_break_signal.emit()
                self.app.unlock_break_signal.emit()

    def check_session_timeout(self):
        if self.reminding or self.on_break:
            return

        if self.session.check_session_timeout():
            if self.break_reminder_enabled:
                self.app.start_break_reminder_signal.emit()

    def handle_frame_events(self, frame_data):
        if frame_data.is_afk_start:
            self.on_afk_start()
        if frame_data.is_afk_finish:
            self.on_afk_finish()
        if frame_data.is_blink_start:
            self.on_blink_start()

    def on_afk_start(self):
        self.afk_time = time.time()

    def on_afk_finish(self):
        self.session.afk_duration += time.time() - self.afk_time

    def on_blink_start(self):
        self.session.blink_count += 1

    def on_reminder_toggle(self, enabled):
        self.break_reminder_enabled = enabled
        self.reminding = False
        self.on_break = False
        self.break_unlocked = False

    def on_reminder_finish(self):
        self.reminding = False

    def on_break_start(self):
        self.on_break = True
        self.break_time = time.time()
        self.session.finish()
        self.update_break_duration()
        self.app.update_finished_session_blink_rate.emit(self.session.get_final_blink_rate())
        self.app.update_finished_session_duration.emit(self.session.get_final_duration())

    def on_break_stop(self):
        self.on_break = False
        self.break_unlocked = False
        self.afk_time = time.time()
        self.session = Session(self.thread.get_setting("session_duration"))

    def on_reminder_start(self):
        self.reminding = True
        self.update_screen_time()

    def on_snooze(self):
        self.session.snooze(self.thread.get_setting("snooze_duration"))

    def on_skip(self):
        self.session.snooze(self.thread.get_setting("session_duration"))


