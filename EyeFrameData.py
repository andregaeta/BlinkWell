class EyeFrameData:
    def __init__(self):
        self.face_detected = False
        self.eye_is_closed = False

        self.is_blink_start = False
        self.is_blink_finish = False
        self.is_afk_start = False
        self.is_afk_finish = False

        self.is_blinking = False
        self.is_afk = False

        self.success = True
