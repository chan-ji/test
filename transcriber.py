import threading
import collections
import queue
import numpy as np
import webrtcvad
import torch

DEFAULT_SAMPLE_RATE = 16000
AGGRESSIVENESS = 3


class LoopbackAudio(threading.Thread):
    def __init__(self, callback, mic, samplerate=DEFAULT_SAMPLE_RATE):
        threading.Thread.__init__(self)
        self.callback = callback
        self.samplerate = samplerate
        self.mic = mic
        self.stop_event = threading.Event()

    def run(self):
        with self.mic.recorder(samplerate=self.samplerate) as recorder:
            while not self.stop_event.is_set():
                data = recorder.record(numframes=640)
                self.callback(data)

    def stop(self):
        self.stop_event.set()


class Audio(object):
    # 마이크에서 오디오를 스트리밍. 데이터는 별도의 스레드로 수신. 버퍼에 저장 및 판독.

    RATE_PROCESS = DEFAULT_SAMPLE_RATE
    CHANNELS = 1
    BLOCKS_PER_SECOND = 50

    def __init__(self, callback=None, device=None, input_rate=RATE_PROCESS):
        def proxy_callback(in_data):
            callback(in_data)

        if callback is None:
            def callback(in_data): return self.buffer_queue.put(in_data)
        self.buffer_queue = queue.Queue()
        self.device = device
        self.input_rate = input_rate
        self.sample_rate = self.RATE_PROCESS
        self.block_size = int(self.RATE_PROCESS /
                              float(self.BLOCKS_PER_SECOND))

        self.soundcard_reader = LoopbackAudio(
            callback=proxy_callback, mic=device, samplerate=self.sample_rate)
        self.soundcard_reader.daemon = True
        self.soundcard_reader.start()

    def read(self):
        #필요한 경우 차단 및 오디오 데이터 블록 반환
        return self.buffer_queue.get()

    def destroy(self):
        self.soundcard_reader.stop()
        self.soundcard_reader.join()

    frame_duration_ms = property(
        lambda self: 1000 * self.block_size // self.sample_rate)


class VADAudio(Audio):
    #음성 활동 감지로 오디오를 필터링 및 조각화.

    def __init__(self, aggressiveness=3, device=None, input_rate=None, event=None):
        super().__init__(device = device, input_rate = input_rate)
        self.event = event
        self.vad = webrtcvad.Vad(aggressiveness)

    def frame_generator(self):
        #마이크에서 모든 오디오 프레임을 생성
        if self.input_rate == self.RATE_PROCESS:
            while True:
                yield self.read()
        else:
            raise Exception("Resampling required")

    def vad_collector(self, padding_ms=300, ratio=0.75, frames=None):
        #하나의 None을 생성 / 분리된 각각의 대사로 구성된 연속 오디오 프레임을 생성.
        #padding_ms의 프레임 비율로 음성 활동 결정. 트리거되기 전에 버퍼를 사용하여 padding_ms를 포함.

        if frames is None:
            frames = self.frame_generator()
        num_padding_frames = padding_ms // self.frame_duration_ms
        ring_buffer = collections.deque(maxlen=num_padding_frames)
        triggered = False

        for frame in frames:
            if len(frame) < 640:
                return

            if self.event.is_set():
                return

            mono_frame = np.mean(frame, axis=1)
            frame = np.int16(mono_frame * 32768)
            is_speech = self.vad.is_speech(frame, self.sample_rate)

            if not triggered:
                ring_buffer.append((frame, is_speech))
                num_voiced = len([f for f, speech in ring_buffer if speech])
                if num_voiced > ratio * ring_buffer.maxlen:
                    triggered = True
                    for f, s in ring_buffer:
                        yield f
                    ring_buffer.clear()

            else:
                yield frame
                ring_buffer.append((frame, is_speech))
                num_unvoiced = len(
                    [f for f, speech in ring_buffer if not speech])
                if num_unvoiced > ratio * ring_buffer.maxlen:
                    triggered = False
                    yield None
                    ring_buffer.clear()


def start_listen(whisper_model, model, get_speech_ts, mic, event, callback):
    print('음성인식 시작')
    f = open("new.txt", 'a', encoding = 'UTF-8')
    # VAD로 오디오 시작
    vad_audio = VADAudio(aggressiveness=AGGRESSIVENESS,
                         device=mic,
                         input_rate=DEFAULT_SAMPLE_RATE,
                         event=event)

    frames = vad_audio.vad_collector()

    wav_data = bytearray()
    for frame in frames:
        if frame is not None:
            wav_data.extend(frame)
        else:
            newsound = np.frombuffer(wav_data, np.int16)
            audio_float32 = Int2Float(newsound)
            time_stamps = get_speech_ts(
                audio_float32, model, sampling_rate=DEFAULT_SAMPLE_RATE)

            if (len(time_stamps) > 0):
                transcript = whisper_model.transcribe(audio=audio_float32, language='Korean')
                text = transcript['text']
                callback(text)
                f.write(text + '\n')
            else:
                pass

            wav_data = bytearray()
    print('음성인식 종료')
    f.close()
    vad_audio.destroy()


def Int2Float(sound):
    _sound = np.copy(sound)
    abs_max = np.abs(_sound).max()
    _sound = _sound.astype('float32')
    if abs_max > 0:
        _sound *= 1/abs_max
    audio_float32 = torch.from_numpy(_sound.squeeze())
    return audio_float32