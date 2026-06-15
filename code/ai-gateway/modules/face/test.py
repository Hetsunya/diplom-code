import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import os
import urllib.request

def download_model():
    model_path = 'face_landmarker.task'
    if not os.path.exists(model_path):
        print("Скачивание модели face_landmarker.task...")
        url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
        try:
            urllib.request.urlretrieve(url, model_path)
            print("Модель успешно скачана.")
        except Exception as e:
            print(f"Ошибка скачивания: {e}")
            return None
    return model_path

def main():
    # 1. Подготовка модели
    model_path = download_model()
    if not model_path:
        return

    print("Инициализация детектора лица...")
    base_options = python.BaseOptions(model_asset_path=model_path)

    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=True,      # Включает распознавание эмоций/микровыражений
        output_facial_transformation_matrixes=True, # Включает данные о повороте головы
        num_faces=1
    )

    try:
        detector = vision.FaceLandmarker.create_from_options(options)
    except Exception as e:
        print(f"Ошибка инициализации: {e}")
        return

    # 2. Запуск камеры
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Не удалось открыть камеру")
        return

    print("Камера запущена. Нажмите 'q' для выхода.")

    while cap.isOpened():
        success, image = cap.read()
        if not success:
            continue

        # Конвертация BGR -> RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Создание объекта Image для MediaPipe
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)

        # Детекция
        detection_result = detector.detect(mp_image)

        # Обработка результатов
        if detection_result.face_landmarks:
            for idx, face_landmarks in enumerate(detection_result.face_landmarks):

                # --- А. Отрисовка точек (опционально) ---
                h, w, _ = image.shape
                for landmark in face_landmarks:
                    x = int(landmark.x * w)
                    y = int(landmark.y * h)
                    # Рисуем маленькие точки
                    cv2.circle(image, (x, y), 1, (0, 255, 0), -1)

                # --- Б. Получение эмоций (Blendshapes) ---
                if detection_result.face_blendshapes:
                    blendshapes = detection_result.face_blendshapes[idx]

                    # Словарь для быстрого поиска
                    scores = {bs.category_name: bs.score for bs in blendshapes}

                    # Примеры метрик:
                    smile = scores.get('smile', 0)
                    jaw_open = scores.get('jawOpen', 0)
                    eye_left = scores.get('eyeClosedLeft', 0)
                    eye_right = scores.get('eyeClosedRight', 0)

                    # Вывод на экран
                    cv2.putText(image, f"Smile: {smile:.2f}", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(image, f"Jaw: {jaw_open:.2f}", (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(image, f"Eyes L/R: {eye_left:.2f}/{eye_right:.2f}", (10, 90),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                # --- В. Поворот головы (Matrix) ---
                # Если нужно точное значение углов, матрицу нужно конвертировать в углы Эйлера.
                # Для демо просто покажем факт наличия данных.
                if detection_result.facial_transformation_matrixes:
                     cv2.putText(image, "Head Pose: Active", (10, 120),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow('Face & Emotion Tracking', image)

        if cv2.waitKey(5) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    detector.close()
    print("Завершено.")

if __name__ == "__main__":
    main()
