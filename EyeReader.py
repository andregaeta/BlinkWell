#region Imports and Globals
import os
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

import cv2
import mediapipe as mp
import math

from EyeFrameData import EyeFrameData

LEFT_EYE_INDEXES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
RIGHT_EYE_INDEXES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]

LEFT_EYE_LEFT_INDEX = 362
LEFT_EYE_RIGHT_INDEX = 263
LEFT_EYE_TOP_INDEX = 386
LEFT_EYE_BOTTOM_INDEX = 374

RIGHT_EYE_LEFT_INDEX = 33
RIGHT_EYE_RIGHT_INDEX = 133
RIGHT_EYE_TOP_INDEX = 159
RIGHT_EYE_BOTTOM_INDEX = 145


#endregion

class EyeReader:

    def __init__(self, app, thread):
        self.thread = thread
        self.app = app
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.mp_face_mesh = mp.solutions.face_mesh

        self.drawing_spec = self.mp_drawing.DrawingSpec(thickness=1, circle_radius=1)
        self.cap = cv2.VideoCapture(0)
        self.face_mesh = self.mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)

        self.frames_with_eyes_open = 0
        self.frames_with_eyes_closed = 0
        self.frames_since_last_blink = 0
        self.eye_is_closed = False
        self.face_detected = False
        self.eye_open_long_enough = True

        return

    def close(self):
        self.face_mesh.close()
        self.cap.release()
        return

    @staticmethod
    def get_pos_at_index(image, face_landmarks, landmark_index):
        landmark = face_landmarks.landmark[landmark_index]

        relative_x = int(landmark.x * image.shape[1])
        relative_y = int(landmark.y * image.shape[0])

        return relative_x, relative_y

    @staticmethod
    def get_ear(image, face_landmarks):
        left_eye_left_pos = EyeReader.get_pos_at_index(image, face_landmarks, LEFT_EYE_LEFT_INDEX)
        left_eye_right_pos = EyeReader.get_pos_at_index(image, face_landmarks, LEFT_EYE_RIGHT_INDEX)
        left_eye_top_pos = EyeReader.get_pos_at_index(image, face_landmarks, LEFT_EYE_TOP_INDEX)
        left_eye_bottom_pos = EyeReader.get_pos_at_index(image, face_landmarks, LEFT_EYE_BOTTOM_INDEX)

        left_eye_length_hor = math.dist(left_eye_left_pos, left_eye_right_pos)
        left_eye_length_vert = math.dist(left_eye_top_pos, left_eye_bottom_pos)

        cv2.line(image, left_eye_left_pos, left_eye_right_pos, (0, 200, 0), 1)
        cv2.line(image, left_eye_top_pos, left_eye_bottom_pos, (0, 200, 0), 1)

        right_eye_left_pos = EyeReader.get_pos_at_index(image, face_landmarks, RIGHT_EYE_LEFT_INDEX)
        right_eye_right_pos = EyeReader.get_pos_at_index(image, face_landmarks, RIGHT_EYE_RIGHT_INDEX)
        right_eye_top_pos = EyeReader.get_pos_at_index(image, face_landmarks, RIGHT_EYE_TOP_INDEX)
        right_eye_bottom_pos = EyeReader.get_pos_at_index(image, face_landmarks, RIGHT_EYE_BOTTOM_INDEX)

        right_eye_length_hor = math.dist(right_eye_left_pos, right_eye_right_pos)
        right_eye_length_vert = math.dist(right_eye_top_pos, right_eye_bottom_pos)

        cv2.line(image, right_eye_left_pos, right_eye_right_pos, (0, 200, 0), 1)
        cv2.line(image, right_eye_top_pos, right_eye_bottom_pos, (0, 200, 0), 1)

        return min((left_eye_length_vert / left_eye_length_hor), (right_eye_length_vert / right_eye_length_hor))

    def analyze_ear(self, ear):
        self.eye_is_closed = ear < self.thread.get_setting("ear_threshold") / 100

    def debug(self, image, face_landmarks):
        if self.eye_is_closed:
            c = (0, 0, 255)
        else:
            c = (0, 255, 0)

        for landmark_index in LEFT_EYE_INDEXES:
            cv2.circle(image, self.get_pos_at_index(image, face_landmarks, landmark_index), radius=2, color=c, thickness=1)

        for landmark_index in RIGHT_EYE_INDEXES:
            cv2.circle(image, self.get_pos_at_index(image, face_landmarks, landmark_index), radius=2, color=c, thickness=1)

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        self.app.update_camera_feed_signal.emit(cv2.flip(image, 1))
        return

    def process_image_landmarks(self, image):
        image.flags.writeable = False
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        if results.multi_face_landmarks:
            self.face_detected = True
            return results.multi_face_landmarks[0]
        else:
            self.face_detected = False
            return results

    def process_frame(self):
        frame_data = EyeFrameData()
        if cv2.waitKey(5) & 0xFF == 27:
            frame_data.success = False
            return frame_data

        success, image = self.cap.read()
        frame_data.success = success

        if not success:
            return frame_data

        face_landmarks = self.process_image_landmarks(image)
        frame_data.face_detected = self.face_detected

        if not self.face_detected:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            self.app.update_camera_feed_signal.emit(cv2.flip(image, 1))
            return frame_data

        ear = self.get_ear(image, face_landmarks)
        self.analyze_ear(ear)
        self.debug(image, face_landmarks)

        frame_data.eye_is_closed = self.eye_is_closed

        return frame_data

