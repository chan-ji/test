import tkinter as tk
import tkinter.filedialog
from ttkbootstrap.constants import *
import ttkbootstrap as ttk
import soundcard as sc
import whisper
import torch
from threading import Thread, Event
from transcriber import start_listen


def prepare():
    # silero-VAD 로드
    model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                  model='silero_vad',
                                  force_reload=False)
    (get_speech_ts, _, _, _, _) = utils

    whisper_model = whisper.load_model("small")

    return model, get_speech_ts, whisper_model


class voicePy(ttk.Window):
    def __init__(self, title, header_text, size, theme="darkly"):
        super().__init__(title=title, size=size, themename=theme)

        self.model, self.get_speech_ts, self.whisper_model = prepare()

        self.create_header(header_text=header_text)

        self.option_val = tk.StringVar()
        self.progress_val = tk.DoubleVar()
        self.progress_label_val = tk.StringVar()
        self.progress = 0
        self.processing = False

        self.mainFrame = self.create_main()
        self.options = self.create_option()
        self.progressLabel, self.progressbar = self.create_progressbar()
        self.start_button, self.stop_button, self.text_click, self.file_button = self.create_buttons()
        self.start_button["state"] = "normal"
        self.stop_button["state"] = "disabled"
        self.text_click["state"] = "normal"
        self.file_button["state"] = "normal"
        self.textbox = self.create_textbox()

        self.progress_label_val.set('준비')

        self.mainloop()

    def callback(self, text):
        self.textbox.insert(END, f'- {text}\n')
        self.textbox.yview(END)

    def start_click(self):
        if self.processing is False:
            self.processing = True
            self.update_progress()
        self.event = Event()
        self.task = Thread(target=start_listen,
                           args=(self.whisper_model,
                                 self.model,
                                 self.get_speech_ts,
                                 self.mics[self.options.current()],
                                 self.event,
                                 self.callback))
        self.task.daemon = True
        self.task.start()
        self.start_button["state"] = "disabled"
        self.stop_button["state"] = "normal"
        self.progress_label_val.set('소리 듣는 중')

    def stop_click(self):
        self.processing = False
        self.event.set()
        self.start_button["state"] = "normal"
        self.stop_button["state"] = "disabled"
        self.progress_label_val.set('준비')

    def file_click(self):
        global new1
        new1 = ttk.Toplevel()
        new1.title("텍스트 파일")
        new1.geometry("700x400")

        text = ttk.Text(new1, width=80, height=15)
        filename = tk.filedialog.askopenfilename(initialdir='C:/Users/CHA EUN JI/PycharmProjects/voice',
                                                 title='파일 열기', filetypes=(('text files', '*.txt'),))
        check = open(filename, 'r', encoding='utf-8')
        str = check.read()
        text.insert(INSERT, str)
        text.pack()

        check.close()
        l1 = ttk.Label(new1, text = text)
        l1.pack()

    def text_click(self):
        global new2
        new2 = ttk.Toplevel()
        new2.title("문자")
        new2.geometry("200x200")

        def textinput() :
            f1 = open("new1.txt", 'a', encoding = 'UTF-8')
            tinput = talk.get("1.0", "end")
            f1.write(tinput + '\n')
            f1.close()


        talk = ttk.Text(new2, height = 10)
        talk.pack()
        btn4 = ttk.Button(new2, text='변환',
                             command=textinput, bootstyle='info')
        btn4.pack()


    def update_progress(self):
        self.progress += 1
        if self.progress > 100:
            self.progress = 0
        self.progress_val.set(self.progress)
        if self.processing:
            self.after(100, self.update_progress)
        else:
            self.progress = 0
            self.progress_val.set(self.progress)

    def create_header(self, header_text):
        titleFrame = ttk.Frame(self, height=100)

        label = ttk.Label(titleFrame, text=header_text, font=(
            'Consolas', 20, 'bold'), anchor='center', bootstyle="inverse-info")
        label.pack(fill='x')
        titleFrame.pack(fill='x')

    def create_main(self):
        mainFrame = ttk.Frame(self)
        mainFrame.pack(expand=True, fill='both', padx=4, pady=4)
        return mainFrame

    def getDevices(self):
        self.mics = sc.all_microphones(include_loopback=True)
        devices = []
        for i in range(len(self.mics)):
            try:
                devices.append(self.mics[i].name)
            except Exception as e:
                print(e)
        return devices

    def create_option(self):
        optionFrame = ttk.Frame(self.mainFrame)
        optionFrame.pack(fill='x')

        optionLabel = ttk.Label(optionFrame, text='장치')
        optionLabel.pack(side=LEFT, padx=(8, 0), pady=(4, 0))
        # 읽기 전용 상태로 combobox 생성
        options = ttk.Combobox(optionFrame, state="readonly",
                               textvariable=self.option_val)
        options['values'] = self.getDevices()
        options.current(0)
        options.pack(side=LEFT, expand=True, fill='x',
                     padx=(8, 8), pady=(4, 0))
        return options

    def create_progressbar(self):
        labelFrame = ttk.Frame(self.mainFrame)
        labelFrame.pack(fill='x')
        progressFrame = ttk.Frame(self.mainFrame)
        progressFrame.pack(fill='x')
        progress_label = ttk.Label(
            labelFrame, textvariable=self.progress_label_val)
        progress_label.pack(side=LEFT, fill='x', padx=(8, 8), pady=(4, 0))
        progressbar = ttk.Progressbar(
            progressFrame, variable=self.progress_val, maximum=100, bootstyle='info')
        progressbar.pack(side=LEFT, expand=True, fill='x',
                         padx=(8, 8), pady=(4, 0))
        return progress_label, progressbar

    def create_buttons(self):
        buttonFrame = ttk.Frame(self.mainFrame)
        buttonFrame.columnconfigure((0, 1, 2, 3, 4, 5), weight=1, uniform='a')
        buttonFrame.pack(fill='x')

        button1 = ttk.Button(buttonFrame, text='시작',
                             command=self.start_click, bootstyle='info')
        button1.grid(row=0, column=1, pady=4)

        button2 = ttk.Button(buttonFrame, text='종료',
                             command=self.stop_click, bootstyle='info')
        button2.grid(row=0, column=2, pady=4)

        button3 = ttk.Button(buttonFrame, text='문자',
                             command=self.text_click, bootstyle='info')
        button3.grid(row=0, column=3, pady=4)

        button4 = ttk.Button(buttonFrame, text='파일',
                             command=self.file_click, bootstyle='info')
        button4.grid(row=0, column=4, pady=4)

        return button1, button2, button3, button4

    def create_textbox(self):
        textbox = ttk.ScrolledText(self.mainFrame, font=(
            'Consolar', 12, 'bold'))
        textbox.config(spacing1=10, spacing2=10, spacing3=10)
        textbox.pack(expand=True, fill='both', padx=8, pady=(4, 8))
        return textbox


voicePy(title='음성인식을 이용한 문자 변환 시스템', size=(800, 600),
          header_text='음성인식을 이용한 문자 변환 시스템', theme='darkly')