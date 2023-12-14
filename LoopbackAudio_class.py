import threading

SAMPLE_RATE = 16000


class LoopbackAudio(threading.Thread):
    def __init__(self, callback, device, samplerate=SAMPLE_RATE):
        threading.Thread.__init__(self)
        self.callback = callback
        self.samplerate = samplerate
        self.mics = sc.all_microphones(include_loopback=True)
        self.mic_index = device
        self.stop_event = threading.Event()

    def run(self):
        if self.mic_index == None:
            mic = sc.default_microphone()
        else:
            mic = self.mics[self.mic_index]
        with mic.recorder(samplerate=self.samplerate) as recorder:
            while not self.stop_event.is_set():
                data = recorder.record(numframes=640)
                self.callback(data)

    def stop(self):
        self.stop_event.set()