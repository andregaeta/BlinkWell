# fix slow camera startup
# alternative is using cv2.VideoCapture(0, cv2.CAP_DSHOW)
import os
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

import cv2
import mediapipe as mp
import math

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

BLINK_EAR_THRESHOLD = 0.20

FRAMES_WITH_EYES_CLOSED = 0
FRAMES_WITH_EYES_OPEN = 0
MIN_FRAMES_BETWEEN_BLINKS = 6


def get_pos_at_index(face_landmarks, landmark_index):
    landmark = face_landmarks.landmark[landmark_index]

    relative_x = int(landmark.x * image.shape[1])
    relative_y = int(landmark.y * image.shape[0])

    return relative_x, relative_y


def get_ear(img, face_landmarks):
    left_eye_left_pos = get_pos_at_index(face_landmarks, LEFT_EYE_LEFT_INDEX)
    left_eye_right_pos = get_pos_at_index(face_landmarks, LEFT_EYE_RIGHT_INDEX)
    left_eye_top_pos = get_pos_at_index(face_landmarks, LEFT_EYE_TOP_INDEX)
    left_eye_bottom_pos = get_pos_at_index(face_landmarks, LEFT_EYE_BOTTOM_INDEX)

    left_eye_length_hor = math.dist(left_eye_left_pos, left_eye_right_pos)
    left_eye_length_vert = math.dist(left_eye_top_pos, left_eye_bottom_pos)

    cv2.line(img, left_eye_left_pos, left_eye_right_pos, (0, 200, 0), 1)
    cv2.line(img, left_eye_top_pos, left_eye_bottom_pos, (0, 200, 0), 1)

    right_eye_left_pos = get_pos_at_index(face_landmarks, RIGHT_EYE_LEFT_INDEX)
    right_eye_right_pos = get_pos_at_index(face_landmarks, RIGHT_EYE_RIGHT_INDEX)
    right_eye_top_pos = get_pos_at_index(face_landmarks, RIGHT_EYE_TOP_INDEX)
    right_eye_bottom_pos = get_pos_at_index(face_landmarks, RIGHT_EYE_BOTTOM_INDEX)

    right_eye_length_hor = math.dist(right_eye_left_pos, right_eye_right_pos)
    right_eye_length_vert = math.dist(right_eye_top_pos, right_eye_bottom_pos)

    cv2.line(img, right_eye_left_pos, right_eye_right_pos, (0, 200, 0), 1)
    cv2.line(img, right_eye_top_pos, right_eye_bottom_pos, (0, 200, 0), 1)

    return min((left_eye_length_vert / left_eye_length_hor), (right_eye_length_vert / right_eye_length_hor))


def on_blink():
    return


mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_face_mesh = mp.solutions.face_mesh

drawing_spec = mp_drawing.DrawingSpec(thickness=1, circle_radius=1)
cap = cv2.VideoCapture(0)
face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)

while cap.isOpened():

    if cv2.waitKey(5) & 0xFF == 27:
        break

    success, image = cap.read()
    if not success:
        continue

    image.flags.writeable = False
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(image)
    image.flags.writeable = True
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    if not results.multi_face_landmarks:
        print("Face not found.")
        cv2.imshow('MediaPipe Face Mesh', cv2.flip(image, 1))
        continue

    face_landmarks = results.multi_face_landmarks[0]
    ear = get_ear(image, face_landmarks)

    c = (0, 255, 0)
    if ear < BLINK_EAR_THRESHOLD:
        if FRAMES_WITH_EYES_CLOSED == 0 and (FRAMES_WITH_EYES_OPEN > MIN_FRAMES_BETWEEN_BLINKS):
            c = (0, 0, 255)
            on_blink()

        FRAMES_WITH_EYES_OPEN = 0
        FRAMES_WITH_EYES_CLOSED += 1
    else:
        FRAMES_WITH_EYES_CLOSED = 0
        FRAMES_WITH_EYES_OPEN += 1

    for landmark_index in LEFT_EYE_INDEXES:
        cv2.circle(image, get_pos_at_index(face_landmarks, landmark_index), radius=2, color=c, thickness=1)

    for landmark_index in RIGHT_EYE_INDEXES:
        cv2.circle(image, get_pos_at_index(face_landmarks, landmark_index), radius=2, color=c, thickness=1)

    cv2.imshow('MediaPipe Face Mesh', cv2.flip(image, 1))

face_mesh.close()
cap.release()
