import audioop
import json
import os
import tempfile
from urllib.error import URLError
from urllib.request import urlopen
import uuid

from requests import HTTPError, Request
from custom_speech_recognition.MicrophoneClasses import Microphone

from custom_speech_recognition.RecognizerClasses import Recognizer
from custom_speech_recognition.exceptions import RequestError, UnknownValueError


@staticmethod
def list_microphone_names():
    """
    Returns a list of the names of all available microphones. For microphones where the name can't be retrieved, the list entry contains ``None`` instead.

    The index of each microphone's name in the returned list is the same as its device index when creating a ``Microphone`` instance - if you want to use the microphone at index 3 in the returned list, use ``Microphone(device_index=3)``.
    """
    audio = Microphone.get_pyaudio().PyAudio()
    try:
        result = []
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            result.append(device_info.get("name"))
    finally:
        audio.terminate()
    return result


@staticmethod
def list_working_microphones():
    """
    Returns a dictionary mapping device indices to microphone names, for microphones that are currently hearing sounds. When using this function, ensure that your microphone is unmuted and make some noise at it to ensure it will be detected as working.

    Each key in the returned dictionary can be passed to the ``Microphone`` constructor to use that microphone. For example, if the return value is ``{3: "HDA Intel PCH: ALC3232 Analog (hw:1,0)"}``, you can do ``Microphone(device_index=3)`` to use that microphone.
    """
    pyaudio_module = Microphone.get_pyaudio()
    audio = pyaudio_module.PyAudio()
    try:
        result = {}
        for device_index in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(device_index)
            device_name = device_info.get("name")
            assert (
                isinstance(device_info.get("defaultSampleRate"), (float, int))
                and device_info["defaultSampleRate"] > 0
            ), "Invalid device info returned from PyAudio: {}".format(device_info)
            try:
                # read audio
                pyaudio_stream = audio.open(
                    input_device_index=device_index,
                    channels=1,
                    format=pyaudio_module.paInt16,
                    rate=int(device_info["defaultSampleRate"]),
                    input=True,
                )
                try:
                    buffer = pyaudio_stream.read(1024)
                    if not pyaudio_stream.is_stopped():
                        pyaudio_stream.stop_stream()
                finally:
                    pyaudio_stream.close()
            except Exception:
                continue

            # compute RMS of debiased audio
            energy = -audioop.rms(buffer, 2)
            energy_bytes = bytes([energy & 0xFF, (energy >> 8) & 0xFF])
            debiased_energy = audioop.rms(
                audioop.add(buffer, energy_bytes * (len(buffer) // 2), 2), 2
            )

            if debiased_energy > 30:  # probably actually audio
                result[device_index] = device_name
    finally:
        audio.terminate()
    return result


def recognize_api(
    self,
    audio_data,
    client_access_token,
    language="en",
    session_id=None,
    show_all=False,
):
    wav_data = audio_data.get_wav_data(convert_rate=16000, convert_width=2)
    url = "https://api.api.ai/v1/query"
    while True:
        boundary = uuid.uuid4().hex
        if boundary.encode("utf-8") not in wav_data:
            break
    if session_id is None:
        session_id = uuid.uuid4().hex
    data = (
        b"--"
        + boundary.encode("utf-8")
        + b"\r\n"
        + b'Content-Disposition: form-data; name="request"\r\n'
        + b"Content-Type: application/json\r\n"
        + b"\r\n"
        + b'{"v": "20150910", "sessionId": "'
        + session_id.encode("utf-8")
        + b'", "lang": "'
        + language.encode("utf-8")
        + b'"}\r\n'
        + b"--"
        + boundary.encode("utf-8")
        + b"\r\n"
        + b'Content-Disposition: form-data; name="voiceData"; filename="audio.wav"\r\n'
        + b"Content-Type: audio/wav\r\n"
        + b"\r\n"
        + wav_data
        + b"\r\n"
        + b"--"
        + boundary.encode("utf-8")
        + b"--\r\n"
    )
    request = Request(
        url,
        data=data,
        headers={
            "Authorization": "Bearer {}".format(client_access_token),
            "Content-Length": str(len(data)),
            "Expect": "100-continue",
            "Content-Type": "multipart/form-data; boundary={}".format(boundary),
        },
    )
    try:
        response = urlopen(request, timeout=10)
    except HTTPError as e:
        raise RequestError("recognition request failed: {}".format(e.reason))
    except URLError as e:
        raise RequestError("recognition connection failed: {}".format(e.reason))
    response_text = response.read().decode("utf-8")
    result = json.loads(response_text)
    if show_all:
        return result
    if (
        "status" not in result
        or "errorType" not in result["status"]
        or result["status"]["errorType"] != "success"
    ):
        raise UnknownValueError()
    return result["result"]["resolvedQuery"]


Recognizer.recognize_api = classmethod(
    recognize_api
)  # API.AI Speech Recognition is deprecated/not recommended as of 3.5.0, and currently is only optionally available for paid plans


class PortableNamedTemporaryFile(object):
    """Limited replacement for ``tempfile.NamedTemporaryFile``, except unlike ``tempfile.NamedTemporaryFile``, the file can be opened again while it's currently open, even on Windows."""

    def __init__(self, mode="w+b"):
        self.mode = mode

    def __enter__(self):
        # create the temporary file and open it
        file_descriptor, file_path = tempfile.mkstemp()
        self._file = os.fdopen(file_descriptor, self.mode)

        # the name property is a public field
        self.name = file_path
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._file.close()
        os.remove(self.name)

    def write(self, *args, **kwargs):
        return self._file.write(*args, **kwargs)

    def writelines(self, *args, **kwargs):
        return self._file.writelines(*args, **kwargs)

    def flush(self, *args, **kwargs):
        return self._file.flush(*args, **kwargs)
