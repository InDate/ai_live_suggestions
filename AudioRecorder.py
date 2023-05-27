from custom_speech_recognition.MicrophoneClasses import Microphone
from custom_speech_recognition.RecognizerClasses import Recognizer
from custom_speech_recognition.audio import AudioData

import sounddevice as sd
from datetime import datetime

RECORD_TIMEOUT = 3
ENERGY_THRESHOLD = 1000
DYNAMIC_ENERGY_THRESHOLD = False


class BaseRecorder:
    def __init__(self, source, source_name):
        self.recorder = Recognizer()
        self.recorder.energy_threshold = ENERGY_THRESHOLD
        self.recorder.dynamic_energy_threshold = DYNAMIC_ENERGY_THRESHOLD
        self.source = source
        self.source_name = source_name

    def adjust_for_noise(self, device_name, msg):
        print(f"[INFO] Adjusting for ambient noise from {device_name}. " + msg)
        with self.source:
            self.recorder.adjust_for_ambient_noise(self.source)
        print(f"[INFO] Completed ambient noise adjustment for {device_name}.")

    def record_into_queue(self, audio_queue):
        def record_callback(_, audio: AudioData) -> None:
            data = audio.get_raw_data()
            audio_queue.put((self.source_name, data, datetime.utcnow()))

        self.recorder.listen_in_background(
            self.source, record_callback, phrase_time_limit=RECORD_TIMEOUT
        )


class DefaultMicRecorder(BaseRecorder):
    def __init__(self):
        super().__init__(source=Microphone(sample_rate=16000), source_name="You")
        self.adjust_for_noise(
            "Default Mic", "Please make some noise from the Default Mic..."
        )


class DefaultSpeakerRecorder(BaseRecorder):
    def __init__(self):
        default_speakers = sd.default.device[1]
        default_speakers_info = sd.query_devices(default_speakers, "input")

        source = Microphone(
            speaker=True,
            device_index=default_speakers,
            sample_rate=int(default_speakers_info["default_samplerate"]),
            chunk_size=default_speakers_info["max_input_channels"],
        )
        super().__init__(source=source, source_name="Speaker")
        self.adjust_for_noise(
            "Default Speaker",
            "Please make or play some noise from the Default Speaker...",
        )
