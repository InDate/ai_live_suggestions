from custom_speech_recognition.AudioSource import AudioSource
import soundcard as sc
import sounddevice as sd


class Microphone(AudioSource):
    """
    Creates a new ``Microphone`` instance, which represents a physical microphone on the computer. Subclass of ``AudioSource``.

    This will throw an ``AttributeError`` if you don't have PyAudio 0.2.11 or later installed.

    If ``device_index`` is unspecified or ``None``, the default microphone is used as the audio source. Otherwise, ``device_index`` should be the index of the device to use for audio input.

    A device index is an integer between 0 and ``pyaudio.get_device_count() - 1`` (assume we have used ``import pyaudio`` beforehand) inclusive. It represents an audio device such as a microphone or speaker. See the `PyAudio documentation <http://people.csail.mit.edu/hubert/pyaudio/docs/>`__ for more details.

    The microphone audio is recorded in chunks of ``chunk_size`` samples, at a rate of ``sample_rate`` samples per second (Hertz). If not specified, the value of ``sample_rate`` is determined automatically from the system's microphone settings.

    Higher ``sample_rate`` values result in better audio quality, but also more bandwidth (and therefore, slower recognition). Additionally, some CPUs, such as those in older Raspberry Pi models, can't keep up if this value is too high.

    Higher ``chunk_size`` values help avoid triggering on rapidly changing ambient noise, but also makes detection less sensitive. This value, generally, should be left at its default.
    """

    def __init__(
        self,
        device_index=None,
        sample_rate=None,
        chunk_size=512,
        channels=1,
        speaker=False,
    ):
        self.speaker = speaker
        self.device_index = device_index
        self.channels = channels
        self.CHUNK = chunk_size

        devices = sd.query_devices()
        count = len(devices)

        if device_index is not None:
            assert (
                0 <= device_index < count
            ), "Device index out of range ({} devices available; device index should be between 0 and {} inclusive)".format(
                count, count - 1
            )

        if sample_rate is None:
            device_info = (
                devices[device_index] if device_index is not None else sd.default.device
            )
            default_sample_rate = devices[sd.default.device[0]]["default_samplerate"]
            assert (
                isinstance(default_sample_rate, (float, int))
                and default_sample_rate > 0
            ), "Invalid device info returned from sounddevice: {}".format(device_info)
            sample_rate = int(default_sample_rate)

        self.SAMPLE_RATE = sample_rate
        self.format = "int16"
        self.SAMPLE_WIDTH = 2  # 16-bit int sampling (2 bytes)

        self.audio = None
        self.stream = None

    def __enter__(self):
        assert (
            self.stream is None
        ), "This audio source is already inside a context manager"

        self.audio = sd

        try:
            if self.speaker:
                self.stream = self.audio.InputStream(
                    device=1,
                    channels=2,
                    dtype=self.format,  # You may need to adjust the format to match sounddevice's data types (e.g., 'float32')
                    samplerate=self.SAMPLE_RATE,
                    blocksize=self.CHUNK,
                )
            else:
                self.stream = self.audio.InputStream(
                    device=self.device_index,
                    channels=1,
                    dtype=self.format,  # You may need to adjust the format to match sounddevice's data types (e.g., 'float32')
                    samplerate=self.SAMPLE_RATE,
                    blocksize=self.CHUNK,
                )
            self.stream.start()
        except Exception:
            self.stream.close()
            self.audio.stop()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self.stream.close()
        finally:
            self.audio.stop()
            self.stream = None
