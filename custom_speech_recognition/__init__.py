#!/usr/bin/env python3

__author__ = "Anthony Zhang (Uberi)"
__version__ = "3.10.0"
__license__ = "BSD"

from custom_speech_recognition import AudioFile
from custom_speech_recognition import AudioSource
from custom_speech_recognition.MicrophoneClasses import Microphone
from custom_speech_recognition.RecognizerClasses import Recognizer
from custom_speech_recognition.utils import PortableNamedTemporaryFile


Microphone(AudioSource)
AudioFile(AudioSource)
Recognizer(AudioSource)
PortableNamedTemporaryFile(object)
