import os
import re
import shlex
import subprocess
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox


# ================== BASE PATHS (RELATIVE) ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

WHISPER_BIN = os.path.join(BASE_DIR, "whisper", "whisper-cli")
WHISPER_MODEL = os.path.join(BASE_DIR, "whisper", "ggml-base.en.bin")

PIPER_BIN = os.path.join(BASE_DIR, "piper", "piper")
PIPER_VOICE = os.path.join(BASE_DIR, "piper", "en_US-lessac-medium.onnx")


# ================== CONFIG ==================
REC_RATE = "16000"
SILENCE_STOP_SECONDS = 1.0
SILENCE_THRESHOLD = "1%"

TMP_DIR = "/tmp/speech_assist"
os.makedirs(TMP_DIR, exist_ok=True)
REC_WAV = os.path.join(TMP_DIR, "answer.wav")
OUT_BASE = os.path.join(TMP_DIR, "answer")
OUT_TXT = OUT_BASE + ".txt"
QUESTION_WAV = os.path.join(TMP_DIR, "question_tts.wav")


# ================== HELPERS ==================
def safe_name(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^A-Za-z0-9_\-]", "", s)
    return s or "Untitled"


def clean_text(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    if not t:
        return ""
    t = t[0].upper() + t[1:]
    if not re.search(r"[.!?]\s*$", t):
        t += "."
    return t


def verify_runtime_files():
    missing = []
    for path in [WHISPER_BIN, WHISPER_MODEL, PIPER_BIN, PIPER_VOICE]:
        if not os.path.exists(path):
            missing.append(path)
    return missing


def detect_record_device():
    override = os.environ.get("SPEECH_ASSIST_MIC", "").strip()
    if override:
        return override, f"Manual: {override}"

    try:
        output = subprocess.check_output(["arecord", "-l"], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return None, "Default input"

    devices = []
    for line in output.splitlines():
        m = re.search(r"card (\d+): .*?, device (\d+): (.+)", line)
        if not m:
            continue
        card = m.group(1)
        device = m.group(2)
        desc = m.group(3).strip()
        dev_name = f"plughw:{card},{device}"

        score = 0
        lower = line.lower()
        if "usb" in lower:
            score += 3
        if "headset" in lower:
            score += 3
        if "logitech" in lower:
            score += 3
        if "analog" in lower:
            score += 1

        devices.append((score, dev_name, desc))

    if not devices:
        return None, "Default input"

    devices.sort(key=lambda x: x[0], reverse=True)
    best = devices[0]
    return best[1], f"{best[2]} ({best[1]})"


def whisper_transcribe(wav_path: str) -> str:
    subprocess.run(
        [
            WHISPER_BIN,
            "-m", WHISPER_MODEL,
            "-f", wav_path,
            "--language", "en",
            "--output-txt",
            "--output-file", OUT_BASE,
        ],
        cwd=os.path.dirname(WHISPER_BIN),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if not os.path.exists(OUT_TXT):
        return ""
    with open(OUT_TXT, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


# ================== SETUP DIALOG (QUESTION BUILDER) ==================
class SetupDialog:
    def __init__(self, parent, subject_var, student_var, questions, on_apply_cb, get_save_folder_text_cb):
        self.parent = parent
        self.subject_var = subject_var
        self.student_var = student_var
        self.on_apply_cb = on_apply_cb
        self.get_save_folder_text_cb = get_save_folder_text_cb

        self.questions = [q.copy() for q in questions] if questions else []
        if not self.questions:
            self.questions = [{"label": "Q1", "text": ""}]

        self.current_index = 0
        self.updating_editor = False

        self.win = tk.Toplevel(parent)
        self.win.title("Setup - Question Builder")
        self.win.transient(parent)
        self.win.grab_set()

        sw = parent.winfo_screenwidth()
        sh = parent.winfo_screenheight()
        w = min(980, sw - 100)
        h = min(680, sh - 100)
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.win.geometry(f"{w}x{h}+{x}+{y}")
        self.win.minsize(780, 560)

        self.win.columnconfigure(0, weight=1)
        self.win.rowconfigure(1, weight=1)

        self.build_ui()
        self.refresh_question_list()
        self.load_current_question_into_editor()

        self._tick()
        self.win.protocol("WM_DELETE_WINDOW", self.close)

    def build_ui(self):
        top = ttk.Frame(self.win, padding=12)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)
        top.columnconfigure(3, weight=1)

        ttk.Label(top, text="Subject").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.subject_var).grid(row=0, column=1, sticky="ew", padx=(8, 20))
        ttk.Label(top, text="Student").grid(row=0, column=2, sticky="w")
        ttk.Entry(top, textvariable=self.student_var).grid(row=0, column=3, sticky="ew", padx=(8, 0))

        main = ttk.Frame(self.win, padding=(12, 0, 12, 10))
        main.grid(row=1, column=0, sticky="nsew")
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        left = ttk.Frame(main)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        left.rowconfigure(2, weight=1)

        ttk.Label(left, text="Questions").grid(row=0, column=0, sticky="w", pady=(0, 8))

        list_btns = ttk.Frame(left)
        list_btns.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(list_btns, text="Add", width=10, command=self.add_question).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(list_btns, text="Remove", width=10, command=self.remove_question).grid(row=0, column=1)

        list_frame = ttk.Frame(left)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.question_listbox = tk.Listbox(list_frame, width=22, height=18, exportselection=False, font=("Arial", 12))
        self.question_listbox.grid(row=0, column=0, sticky="nsew")
        self.question_listbox.bind("<<ListboxSelect>>", self.on_select_question)

        list_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.question_listbox.yview)
        list_scroll.grid(row=0, column=1, sticky="ns")
        self.question_listbox.configure(yscrollcommand=list_scroll.set)

        right = ttk.Frame(main)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)

        ttk.Label(right, text="Question label").grid(row=0, column=0, sticky="w")
        self.label_var = tk.StringVar()
        self.label_entry = ttk.Entry(right, textvariable=self.label_var)
        self.label_entry.grid(row=1, column=0, sticky="ew", pady=(4, 10))
        self.label_entry.bind("<KeyRelease>", self.on_label_change)

        ttk.Label(right, text="Question content").grid(row=2, column=0, sticky="w", pady=(0, 6))

        editor_frame = ttk.Frame(right)
        editor_frame.grid(row=3, column=0, sticky="nsew")
        editor_frame.columnconfigure(0, weight=1)
        editor_frame.rowconfigure(0, weight=1)

        self.editor = tk.Text(editor_frame, wrap="word", font=("Arial", 13))
        self.editor.grid(row=0, column=0, sticky="nsew")
        self.editor.bind("<<Modified>>", self.on_editor_change)

        editor_scroll = ttk.Scrollbar(editor_frame, orient="vertical", command=self.editor.yview)
        editor_scroll.grid(row=0, column=1, sticky="ns")
        self.editor.configure(yscrollcommand=editor_scroll.set)

        bottom = ttk.Frame(self.win, padding=(12, 0, 12, 12))
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)

        self.save_label = ttk.Label(bottom, text=self.get_save_folder_text_cb(), style="Small.TLabel")
        self.save_label.grid(row=0, column=0, sticky="w")

        btns = ttk.Frame(bottom)
        btns.grid(row=0, column=1, sticky="e")
        ttk.Button(btns, text="Cancel", width=12, command=self.close).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Apply", width=12, command=self.apply).pack(side="left")

    def _tick(self):
        try:
            self.save_label.config(text=self.get_save_folder_text_cb())
            self.win.after(700, self._tick)
        except Exception:
            pass

    def refresh_question_list(self):
        self.question_listbox.delete(0, "end")
        for i, q in enumerate(self.questions, start=1):
            label = (q.get("label") or f"Q{i}").strip()
            self.question_listbox.insert("end", label)
        if self.questions:
            self.question_listbox.selection_clear(0, "end")
            self.question_listbox.selection_set(self.current_index)
            self.question_listbox.activate(self.current_index)

    def save_current_editor_to_model(self):
        if not self.questions:
            return
        self.questions[self.current_index]["label"] = self.label_var.get().strip() or f"Q{self.current_index + 1}"
        self.questions[self.current_index]["text"] = self.editor.get("1.0", "end").rstrip()

    def load_current_question_into_editor(self):
        if not self.questions:
            return
        self.updating_editor = True
        q = self.questions[self.current_index]
        self.label_var.set(q.get("label", f"Q{self.current_index + 1}"))
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", q.get("text", ""))
        self.editor.edit_modified(False)
        self.updating_editor = False

    def on_select_question(self, event=None):
        sel = self.question_listbox.curselection()
        if not sel:
            return
        new_index = sel[0]
        if new_index == self.current_index:
            return
        self.save_current_editor_to_model()
        self.current_index = new_index
        self.load_current_question_into_editor()

    def on_label_change(self, event=None):
        if not self.questions:
            return
        self.questions[self.current_index]["label"] = self.label_var.get().strip() or f"Q{self.current_index + 1}"
        self.refresh_question_list()

    def on_editor_change(self, event=None):
        if self.updating_editor:
            return
        if self.editor.edit_modified():
            if self.questions:
                self.questions[self.current_index]["text"] = self.editor.get("1.0", "end").rstrip()
            self.editor.edit_modified(False)

    def add_question(self):
        self.save_current_editor_to_model()
        new_num = len(self.questions) + 1
        self.questions.append({"label": f"Q{new_num}", "text": ""})
        self.current_index = len(self.questions) - 1
        self.refresh_question_list()
        self.load_current_question_into_editor()

    def remove_question(self):
        if len(self.questions) <= 1:
            messagebox.showinfo("Cannot remove", "At least one question must remain.")
            return
        del self.questions[self.current_index]
        self.current_index = max(0, min(self.current_index, len(self.questions) - 1))
        for i, q in enumerate(self.questions, start=1):
            if not q.get("label", "").strip():
                q["label"] = f"Q{i}"
        self.refresh_question_list()
        self.load_current_question_into_editor()

    def apply(self):
        self.save_current_editor_to_model()

        cleaned = []
        for i, q in enumerate(self.questions, start=1):
            label = q.get("label", "").strip() or f"Q{i}"
            text = q.get("text", "").strip()
            if text:
                cleaned.append({"label": label, "text": text})

        if not cleaned:
            messagebox.showinfo("No questions", "Please add at least one question with content.")
            return

        ok = self.on_apply_cb(cleaned)
        if ok:
            self.close()

    def close(self):
        try:
            self.win.grab_release()
        except Exception:
            pass
        self.win.destroy()


# ================== MAIN APP ==================
class SpeechAssistApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Erindale College Speech Assist (Exam)")

        missing = verify_runtime_files()
        if missing:
            messagebox.showerror(
                "Missing files",
                "Some required runtime files are missing:\n\n" + "\n".join(missing)
            )
            root.destroy()
            return

        self.record_device, self.record_device_label = detect_record_device()

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = min(max(int(sw * 0.78), 980), sw - 60)
        h = min(max(int(sh * 0.88), 700), sh - 60)
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.minsize(860, 640)

        self.status_var = tk.StringVar(value="Ready")
        self.save_hint_var = tk.StringVar(value="")
        self.subject_var = tk.StringVar(value="")
        self.student_var = tk.StringVar(value="")

        self.questions = []
        self.current_idx = 0
        self.q_select_var = tk.StringVar(value="Q01")
        self.session_dir = None

        self.is_recording = False
        self.recording_proc = None
        self.read_proc = None
        self.setup_dialog = None

        self.apply_theme_and_styles()
        self.build_ui()

        self.root.after(250, self.open_setup)
        self.root.after(500, self.disable_network_on_startup)

    def apply_theme_and_styles(self):
        self.style = ttk.Style()
        for theme in ("clam", "default"):
            if theme in self.style.theme_names():
                try:
                    self.style.theme_use(theme)
                    break
                except Exception:
                    pass

        self.root.option_add("*Font", ("Arial", 13))

        self.style.configure("Primary.TButton", font=("Arial", 13, "bold"), padding=(14, 10))
        self.style.configure("Recording.TButton", font=("Arial", 13, "bold"), padding=(14, 10))
        self.style.configure("Nav.TButton", font=("Arial", 11), padding=(8, 6))
        self.style.configure("Tiny.TButton", font=("Arial", 10), padding=(6, 4))
        self.style.configure("Title.TLabel", font=("Arial", 18, "bold"))
        self.style.configure("Section.TLabel", font=("Arial", 20, "bold"))
        self.style.configure("Small.TLabel", font=("Arial", 10))
        self.style.configure("Muted.TLabel", font=("Arial", 11))

        try:
            self.style.configure("Primary.TButton", foreground="white", background="#1E5AA8")
            self.style.map("Primary.TButton", background=[("active", "#184C8C"), ("pressed", "#123A6B")])

            self.style.configure("Recording.TButton", foreground="white", background="#C0392B")
            self.style.map("Recording.TButton", background=[("active", "#E74C3C"), ("pressed", "#A93226")])
        except Exception:
            pass

    def disable_network_on_startup(self):
        def worker():
            try:
                subprocess.run(["sudo", "nmcli", "radio", "wifi", "off"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
                subprocess.run(["sudo", "nmcli", "networking", "off"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=(12, 10))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Erindale College Speech Assist (Exam)", style="Title.TLabel").grid(row=0, column=0, sticky="w")

        right = ttk.Frame(header)
        right.grid(row=0, column=1, sticky="e")
        ttk.Button(right, text="Setup", width=12, style="Nav.TButton", command=self.open_setup).pack(side="left", padx=(0, 12))
        ttk.Label(right, textvariable=self.status_var, style="Muted.TLabel").pack(side="left")

        self.paned = ttk.Panedwindow(self.root, orient="vertical")
        self.paned.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        top = ttk.Frame(self.paned)
        top.columnconfigure(0, weight=1)
        top.rowconfigure(1, weight=1)

        q_controls = ttk.Frame(top, padding=(10, 6))
        q_controls.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        q_controls.columnconfigure(1, weight=1)

        left = ttk.Frame(q_controls)
        left.grid(row=0, column=0, sticky="w")

        ttk.Label(left, text="Question:").grid(row=0, column=0, sticky="w")
        self.q_combo = ttk.Combobox(left, textvariable=self.q_select_var, state="disabled", width=12)
        self.q_combo.grid(row=0, column=1, sticky="w", padx=(8, 12))
        self.q_combo.bind("<<ComboboxSelected>>", self.on_dropdown_select)

        self.btn_read = ttk.Button(left, text="🔊 Read Question", width=16, style="Primary.TButton", command=self.read_current_question)
        self.btn_read.grid(row=0, column=2, rowspan=2, sticky="w", padx=(0, 8))

        self.btn_pause = ttk.Button(left, text="⏸ Pause Reading", width=16, style="Nav.TButton", command=self.pause_reading, state="disabled")
        self.btn_pause.grid(row=0, column=3, rowspan=2, sticky="w", padx=(0, 8))

        ttk.Button(left, text="← Previous", width=10, style="Tiny.TButton", command=self.prev_question).grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Button(left, text="Next →", width=10, style="Tiny.TButton", command=self.next_question).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(6, 0))

        ttk.Label(q_controls, textvariable=self.save_hint_var, style="Small.TLabel").grid(row=0, column=1, sticky="e")

        question_frame = ttk.Frame(top, padding=(16, 8, 16, 12))
        question_frame.grid(row=1, column=0, sticky="nsew")
        question_frame.columnconfigure(0, weight=1)
        question_frame.rowconfigure(1, weight=1)

        self.q_label = ttk.Label(question_frame, text="Q1", style="Section.TLabel")
        self.q_label.grid(row=0, column=0, sticky="w", pady=(0, 8))

        q_text_frame = ttk.Frame(question_frame)
        q_text_frame.grid(row=1, column=0, sticky="nsew")
        q_text_frame.columnconfigure(0, weight=1)
        q_text_frame.rowconfigure(0, weight=1)

        self.q_text = tk.Text(
            q_text_frame,
            wrap="word",
            font=("Arial", 20),
            height=5,
            padx=14,
            pady=14,
            borderwidth=1,
            relief="solid"
        )
        self.q_text.grid(row=0, column=0, sticky="nsew")
        q_scroll = ttk.Scrollbar(q_text_frame, orient="vertical", command=self.q_text.yview)
        q_scroll.grid(row=0, column=1, sticky="ns")
        self.q_text.configure(yscrollcommand=q_scroll.set, state="disabled")

        bottom = ttk.Frame(self.paned)
        bottom.columnconfigure(0, weight=1)
        bottom.rowconfigure(1, weight=1)

        a_controls = ttk.Frame(bottom, padding=(10, 6))
        a_controls.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        self.btn_record = ttk.Button(a_controls, text="🎙 Start Speaking", width=16, style="Primary.TButton", command=self.start_answer_auto)
        self.btn_record.pack(side="left")

        self.btn_stop = ttk.Button(a_controls, text="⏹ Stop Speaking", width=16, style="Nav.TButton", command=self.stop_recording_early, state="disabled")
        self.btn_stop.pack(side="left", padx=(8, 0))

        ttk.Button(a_controls, text="Clear Answer", width=12, style="Nav.TButton",
                   command=lambda: self.a_text.delete("1.0", "end")).pack(side="left", padx=(8, 0))

        answer_frame = ttk.Frame(bottom, padding=(16, 8, 16, 12))
        answer_frame.grid(row=1, column=0, sticky="nsew")
        answer_frame.columnconfigure(0, weight=1)
        answer_frame.rowconfigure(1, weight=1)

        ttk.Label(answer_frame, text="Answer", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))

        a_text_frame = ttk.Frame(answer_frame)
        a_text_frame.grid(row=1, column=0, sticky="nsew")
        a_text_frame.columnconfigure(0, weight=1)
        a_text_frame.rowconfigure(0, weight=1)

        self.a_text = tk.Text(
            a_text_frame,
            wrap="word",
            font=("Arial", 18),
            height=11,
            padx=14,
            pady=14,
            borderwidth=1,
            relief="solid"
        )
        self.a_text.grid(row=0, column=0, sticky="nsew")
        a_scroll = ttk.Scrollbar(a_text_frame, orient="vertical", command=self.a_text.yview)
        a_scroll.grid(row=0, column=1, sticky="ns")
        self.a_text.configure(yscrollcommand=a_scroll.set)

        self.paned.add(top, weight=2)
        self.paned.add(bottom, weight=3)
        self.root.after(250, self._set_initial_split)

    def _set_initial_split(self):
        try:
            h = self.paned.winfo_height()
            if h > 200:
                self.paned.sashpos(0, int(h * 0.34))
        except Exception:
            pass

    def get_save_folder_text(self):
        if self.session_dir:
            return f"Save folder: {self.session_dir}"
        return "Save folder: ~/Desktop/Exam Answers/Student_Subject_YYYY-MM-DD_01"

    def open_setup(self):
        if self.setup_dialog and self.setup_dialog.win.winfo_exists():
            self.setup_dialog.win.lift()
            return
        self.setup_dialog = SetupDialog(
            parent=self.root,
            subject_var=self.subject_var,
            student_var=self.student_var,
            questions=self.questions,
            on_apply_cb=self.apply_questions_from_dialog,
            get_save_folder_text_cb=self.get_save_folder_text,
        )

    def apply_questions_from_dialog(self, question_items) -> bool:
        if not question_items:
            messagebox.showinfo("No questions", "Please add at least one question.")
            return False

        self.questions = question_items
        self.current_idx = 0
        self.session_dir = None
        self.ensure_session_dir()

        values = []
        for i, q in enumerate(self.questions, start=1):
            label = q.get("label", f"Q{i}").strip() or f"Q{i}"
            values.append(label)

        self.q_combo.configure(values=values, state="readonly")
        self.q_select_var.set(values[0])

        self.show_question()
        self.status_var.set(f"Loaded {len(self.questions)} questions")
        return True

    def ensure_session_dir(self):
        if self.session_dir:
            return self.session_dir

        base = os.path.join(os.path.expanduser("~/Desktop"), "Exam Answers")
        os.makedirs(base, exist_ok=True)

        student = safe_name(self.student_var.get())[:20]
        subject = safe_name(self.subject_var.get())[:20]
        today = datetime.now().strftime("%Y-%m-%d")
        counter = 1

        while True:
            folder = f"{student}_{subject}_{today}_{counter:02d}"
            full = os.path.join(base, folder)
            if not os.path.exists(full):
                os.makedirs(full, exist_ok=True)
                self.session_dir = full
                return self.session_dir
            counter += 1

    def response_path(self, qn: int):
        return os.path.join(self.ensure_session_dir(), f"Q{qn:02d}.txt")

    def all_responses_path(self):
        return os.path.join(self.ensure_session_dir(), "ALL.txt")

    def write_response_files(self, qn: int, question: str, answer: str):
        with open(self.response_path(qn), "w", encoding="utf-8") as f:
            f.write(f"Question {qn}\n{question.strip()}\n\nAnswer\n{answer.strip()}\n")

        with open(self.all_responses_path(), "w", encoding="utf-8") as out:
            for i, q in enumerate(self.questions, start=1):
                label = q.get("label", f"Q{i}")
                text = q.get("text", "").strip()

                out.write(f"=== {label} ===\n{text}\n\nAnswer\n")
                rp = self.response_path(i)
                if os.path.exists(rp):
                    with open(rp, "r", encoding="utf-8", errors="ignore") as rf:
                        content = rf.read()
                    parts = content.split("Answer\n", 1)
                    ans = parts[1].strip() if len(parts) == 2 else ""
                    out.write(ans + "\n\n")
                else:
                    out.write("\n\n")

    def show_question(self):
        if not self.questions:
            return

        qn = self.current_idx + 1
        current = self.questions[self.current_idx]
        label = current.get("label", f"Q{qn}").strip() or f"Q{qn}"

        self.q_select_var.set(label)
        self.q_label.config(text=label)

        self.q_text.configure(state="normal")
        self.q_text.delete("1.0", "end")
        self.q_text.insert("1.0", current.get("text", ""))
        self.q_text.configure(state="disabled")

        self.a_text.delete("1.0", "end")
        rp = self.response_path(qn)
        if os.path.exists(rp):
            with open(rp, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            parts = content.split("Answer\n", 1)
            if len(parts) == 2:
                self.a_text.insert("1.0", parts[1].strip())

        self.save_hint_var.set("Answer saved automatically ✓")

    def on_dropdown_select(self, event=None):
        if not self.questions:
            return
        selected = self.q_select_var.get().strip()
        for i, q in enumerate(self.questions):
            if (q.get("label", "").strip() or f"Q{i+1}") == selected:
                self.current_idx = i
                self.show_question()
                break

    def prev_question(self):
        if self.questions and self.current_idx > 0:
            self.current_idx -= 1
            self.show_question()

    def next_question(self):
        if self.questions and self.current_idx < len(self.questions) - 1:
            self.current_idx += 1
            self.show_question()

    def read_current_question(self):
        if not self.questions:
            messagebox.showinfo("No questions", "Open Setup and load questions first.")
            return
        if self.read_proc is not None:
            return

        self.btn_read.configure(state="disabled")
        self.btn_pause.configure(state="normal")
        question_text = self.questions[self.current_idx].get("text", "")

        def worker():
            try:
                self.root.after(0, lambda: self.status_var.set("Reading question..."))
                p = subprocess.Popen(
                    [PIPER_BIN, "--model", PIPER_VOICE, "--output_file", QUESTION_WAV],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    text=True,
                )
                p.stdin.write(question_text)
                p.stdin.close()
                p.wait()

                self.read_proc = subprocess.Popen(
                    ["aplay", QUESTION_WAV],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.read_proc.wait()
            except Exception:
                pass
            finally:
                self.read_proc = None
                self.root.after(0, lambda: self.btn_read.configure(state="normal"))
                self.root.after(0, lambda: self.btn_pause.configure(state="disabled"))
                self.root.after(0, lambda: self.status_var.set("Ready"))

        threading.Thread(target=worker, daemon=True).start()

    def pause_reading(self):
        if self.read_proc is not None:
            try:
                self.read_proc.terminate()
            except Exception:
                pass
            self.read_proc = None
        self.btn_pause.configure(state="disabled")
        self.btn_read.configure(state="normal")
        self.status_var.set("Ready")

    def stop_recording_early(self):
        if not self.is_recording or self.recording_proc is None:
            return
        try:
            self.recording_proc.terminate()
        except Exception:
            pass

    def start_answer_auto(self):
        if not self.questions:
            messagebox.showinfo("No questions", "Open Setup and load questions first.")
            return
        if self.is_recording:
            return

        for f in (REC_WAV, OUT_TXT):
            try:
                os.remove(f)
            except FileNotFoundError:
                pass

        self.is_recording = True
        self.btn_record.configure(text="🔴 Recording...", style="Recording.TButton", state="disabled")
        self.btn_stop.configure(state="normal")
        self.status_var.set("Recording response...")

        device_part = ""
        if self.record_device:
            device_part = f"-D {shlex.quote(self.record_device)} "

        cmd = f"""
        arecord {device_part}-f S16_LE -r {REC_RATE} -c 1 -t wav - 2>/dev/null |
        sox -t wav - -t wav {shlex.quote(REC_WAV)} silence 1 0.1 {SILENCE_THRESHOLD} 1 {SILENCE_STOP_SECONDS} {SILENCE_THRESHOLD}
        """
        proc = subprocess.Popen(cmd, shell=True)
        self.recording_proc = proc

        def watcher():
            proc.wait()

            def finish_ui():
                self.is_recording = False
                self.recording_proc = None
                self.btn_record.configure(text="🎙 Start Speaking", style="Primary.TButton", state="normal")
                self.btn_stop.configure(state="disabled")

            if (not os.path.exists(REC_WAV)) or os.path.getsize(REC_WAV) < 6000:
                self.root.after(0, finish_ui)
                self.root.after(0, lambda: self.status_var.set("Ready"))
                self.root.after(0, lambda: messagebox.showwarning("No audio", "Audio was too short or empty. Please try again."))
                return

            self.root.after(0, lambda: self.status_var.set("Transcribing response..."))
            raw = whisper_transcribe(REC_WAV)
            result = clean_text(raw)

            if not result:
                self.root.after(0, finish_ui)
                self.root.after(0, lambda: self.status_var.set("Ready"))
                self.root.after(0, lambda: messagebox.showwarning("Blank result", "Transcription was blank. Please try again."))
                return

            def apply_result():
                existing = self.a_text.get("1.0", "end").strip()
                new_text = (existing + "\n" + result).strip() if existing else result.strip()

                self.a_text.delete("1.0", "end")
                self.a_text.insert("1.0", new_text)

                qn = self.current_idx + 1
                question_text = self.questions[self.current_idx].get("text", "")
                self.write_response_files(qn, question_text, new_text)

                self.save_hint_var.set("Answer saved automatically ✓")
                self.status_var.set("Ready")
                finish_ui()

            self.root.after(0, apply_result)

        threading.Thread(target=watcher, daemon=True).start()


def main():
    root = tk.Tk()
    SpeechAssistApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
