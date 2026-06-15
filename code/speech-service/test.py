import numpy as np
import pyaudio
from faster_whisper import WhisperModel
import time
import sys
import os

# --- КОНФИГУРАЦИЯ ---
MODEL_SIZE = "medium"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

# Параметры окна
WINDOW_SECONDS = 4.0      # Длина окна для распознавания
STEP_SECONDS = 2.0        # Шаг сдвига (overlap = WINDOW - STEP)
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1024

def main():
    # Подавление предупреждений HF Hub (опционально)
    os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'

    print(f"Загрузка модели {MODEL_SIZE} на {DEVICE}...")
    try:
        model = WhisperModel(
            MODEL_SIZE,
            device=DEVICE,
            compute_type=COMPUTE_TYPE,
        )
        print("Модель успешно загружена.")
    except Exception as e:
        print(f"Ошибка загрузки модели: {e}")
        return

    print("Инициализация микрофона...")
    audio_interface = pyaudio.PyAudio()

    # Фильтр ошибок ALSA (грязный хак, но работает)
    devnull = open(os.devnull, 'w')
    old_stderr = sys.stderr
    sys.stderr = devnull

    try:
        stream = audio_interface.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE
        )
    except Exception as e:
        sys.stderr = old_stderr
        print(f"Ошибка доступа к микрофону: {e}")
        return
    finally:
        sys.stderr = old_stderr

    print(f"Говорите! Окно: {WINDOW_SECONDS}с, Шаг: {STEP_SECONDS}с.")

    buffer = np.array([], dtype=np.float32)
    last_transcribed_time = 0

    try:
        while True:
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            audio_chunk = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            buffer = np.concatenate((buffer, audio_chunk))

            current_duration = len(buffer) / SAMPLE_RATE

            # Если накопили достаточно для полного окна
            if current_duration >= WINDOW_SECONDS:

                # Берем сегмент для обработки (последние WINDOW_SECONDS)
                segment = buffer[-int(SAMPLE_RATE * WINDOW_SECONDS):]

                # Транскрибация
                segments, info = model.transcribe(
                    segment,
                    language="ru",
                    beam_size=1,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500)
                )

                text = " ".join([segment.text for segment in segments]).strip()

                if text:
                    # Простая эвристика: выводим текст, если он изменился
                    # В идеале нужно сравнивать с предыдущим output, но для теста хватит этого
                    print(f"\r[{time.strftime('%H:%M:%S')}] {text}   ", flush=True)

                # Сдвигаем буфер на STEP_SECONDS назад
                # То есть оставляем "хвост" для контекста следующего окна
                keep_samples = int(SAMPLE_RATE * (WINDOW_SECONDS - STEP_SECONDS))
                if keep_samples > 0:
                    buffer = buffer[-keep_samples:]
                else:
                    buffer = np.array([], dtype=np.float32)

    except KeyboardInterrupt:
        print("\nОстановка...")
    finally:
        stream.stop_stream()
        stream.close()
        audio_interface.terminate()
        devnull.close()

if __name__ == "__main__":
    main()
