# Erindale College Speech Assist – User Guide

## 1. Purpose

Erindale College Speech Assist is an offline exam support tool that allows staff to:

- prepare exam questions in advance
- read questions aloud to students
- capture spoken student responses
- save answers automatically by question

It is designed for supported school assessment situations.

---

## 2. Starting the program

Open:

```
Erindale College Speech Assist

```



or run:

```
erindale-speech-assist
```

When the program starts, it will attempt to disable Wi-Fi/networking automatically.

------

## 3. Setting up an exam

Click:

```
Setup
```

In the Setup window:

- enter the **Subject**
- enter the **Student**
- use the Question Builder to prepare questions

### Question Builder controls

- **Add**: add a new question
- **Remove**: remove the selected question
- **Question label**: edit the displayed question name, such as `Q1`, `Short Response 2`, or `Section A`
- **Question content**: enter the full question text, including multiple paragraphs if required

Click:

```
Apply
```

when finished.

------

## 4. Running the exam

Once setup is complete:

- use the **Question** dropdown to jump to a question
- use **Previous** and **Next** to move through questions
- click **Read Question** to read the current question aloud
- click **Pause Reading** to stop playback
- click **Start Speaking** to begin recording a response
- click **Stop Speaking** to stop recording early if needed

When the student stops speaking, the program:

1. ends recording automatically
2. transcribes the response
3. inserts the response into the Answer area
4. saves the answer automatically

------

## 5. Saving and output

Answers are saved automatically to:

```
~/Desktop/Exam Answers/
```

Each exam session creates a folder named like:

```
Student_Subject_YYYY-MM-DD_01
```

Example:

```
Jasper_English_2026-03-17_01
```

Files include:

- `Q01.txt`
- `Q02.txt`
- `Q03.txt`
- `ALL.txt`

`ALL.txt` contains the full set of questions and answers in one document.

------

## 6. Recommended staff workflow

1. Open the program
2. Click **Setup**
3. Enter student and subject
4. Add all questions in order
5. Click **Apply**
6. Read each question aloud as needed
7. Record the student’s response
8. Move to the next question
9. At the end, check the saved files in `Exam Answers`

------

## 7. Good practice tips

- Review all questions before the exam begins
- Keep question labels short and clear
- Test the headset and microphone before each session
- Check that answers appear in the Answer box after speaking
- Confirm the session folder has been created on the Desktop

------

## 8. Troubleshooting

### No sound when reading questions

Check:

- headset/speakers are connected
- system output volume is on
- the correct output device is selected

### Speech is not transcribed

Check:

- microphone is connected
- the microphone is not muted
- the correct input device is detected

You can manually force an input device:

```
export SPEECH_ASSIST_MIC=plughw:1,0
erindale-speech-assist
```

### Nothing is saved

Check that the Desktop contains:

```
Exam Answers
```

### The app says files are missing

The runtime files may not be installed correctly. Re-run installation.

------

## 9. Support

Maintainer: Jasper Lin
 Email: lin.yuxuan@icloud.com
