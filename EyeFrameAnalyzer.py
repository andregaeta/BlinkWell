BLINK_FRAME_THRESHOLD = 1
UNBLINK_FRAME_THRESHOLD = 3

AFK_START_FRAME_THRESHOLD = 20
AFK_FINISH_FRAME_THRESHOLD = 20


class EyeFrameAnalyzer:
    def __init__(self, app, thread):
        self.frames_with_eyes_open = 0
        self.frames_with_eyes_closed = 0
        self.frames_face_undetected = 0
        self.frames_face_detected = 0

        self.is_blinking = False
        self.is_afk = False

    def on_blink_start(self, eye_frame_data):
        self.is_blinking = True
        eye_frame_data.is_blink_start = True

    def on_blink_finish(self, eye_frame_data):
        self.is_blinking = False
        eye_frame_data.is_blink_finish = True

    def on_afk_start(self, eye_frame_data):
        self.is_afk = True
        eye_frame_data.is_afk_start = True

        self.frames_with_eyes_open = 0
        self.frames_with_eyes_closed = 0
        self.is_blinking = False

    def on_afk_finish(self, eye_frame_data):
        self.is_afk = False
        eye_frame_data.is_afk_finish = True

    def tick(self, frame_data):
        if frame_data.face_detected:
            self.frames_face_undetected = 0
            self.frames_face_detected += 1
            if self.frames_face_detected == AFK_FINISH_FRAME_THRESHOLD and self.is_afk:
                self.on_afk_finish(frame_data)
        else:
            self.frames_face_detected = 0
            self.frames_face_undetected += 1
            if self.frames_face_undetected == AFK_START_FRAME_THRESHOLD and not self.is_afk:
                self.on_afk_start(frame_data)

        if frame_data.face_detected:
            if frame_data.eye_is_closed:
                self.frames_with_eyes_open = 0
                self.frames_with_eyes_closed += 1
                if self.frames_with_eyes_closed == BLINK_FRAME_THRESHOLD and not self.is_blinking:
                    self.on_blink_start(frame_data)
            else:
                self.frames_with_eyes_closed = 0
                self.frames_with_eyes_open += 1
                if self.frames_with_eyes_open == UNBLINK_FRAME_THRESHOLD and self.is_blinking:
                    self.on_blink_finish(frame_data)

        frame_data.is_afk = self.is_afk
        frame_data.is_blinking = self.is_blinking

