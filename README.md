# 📚 MCQ Question, Answer & Explanation Extractor

A fast, automated Python tool to scrape and extract MCQ questions, options, answers, and explanations from exam links.

Specially optimized for **Asopori (asopori.com)** and general online MCQ test portals.

---

## 📋 Features

- 🔗 **Direct Terminal Input**: Paste any exam link directly into the terminal.
- 🔍 **`view-source:` Handling**: Automatically strips browser `view-source:` prefixes if copied from address bar.
- ⚡ **Auto `/read` Resolution**: If given an Asopori exam link (e.g. `https://asopori.com/exam/...`), it automatically fetches the questions reading mode page.
- 🎯 **Full Data Extraction**:
  - Question Number & Question Text (Supports both English and Bengali UTF-8 text)
  - Options (`a`, `b`, `c`, `d`, or Bengali `ক`, `খ`, `গ`, `ঘ`)
  - Correct Answer
  - Detailed Explanation (if available on the page)
- 💾 **Multiple Export Formats**:
  - 📄 **TXT** (`exports/<exam_title>.txt`) - Clean reading/print format
  - 📋 **JSON** (`exports/<exam_title>.json`) - Structured data for apps & databases
  - 📝 **Markdown** (`exports/<exam_title>.md`) - Beautiful notes format
  - 📊 **CSV** (`exports/<exam_title>.csv`) - Excel spreadsheet format

---

## 🛠️ Installation & Setup

1. Open your terminal in this directory:
   ```bash
   cd "c:\Users\Arif Academy ICT\Downloads\Asopori exam MCQ"
   ```

2. Install the required Python packages using [`requirements.txt`](file:///c:/Users/Arif%20Academy%20ICT/Downloads/Asopori%20exam%20MCQ/requirements.txt):
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 How to Use

### Method 1: Interactive Terminal Mode (Recommended)
Double-click [`run.bat`](file:///c:/Users/Arif%20Academy%20ICT/Downloads/Asopori%20exam%20MCQ/run.bat) or run:
```bash
python mcq_scraper.py
```
You will be prompted to paste your link:
```text
Enter MCQ Link (or type 'q' / 'exit' to quit): https://asopori.com/exam/english-lesson-mcq-questions-answers-5936/read
```
The scraper will display all questions with answers in color and automatically export them. You can paste link after link without restarting!

### Method 2: Direct Command Line Argument
Pass the link directly in your command:
```bash
python mcq_scraper.py "https://asopori.com/exam/bcs-mcq-questions-answers-6138"
```

Or with `view-source:` prefix:
```bash
python mcq_scraper.py "view-source:https://asopori.com/exam/english-lesson-mcq-questions-answers-7007"
```

---

## 📂 Exported Output Files

All extracted questions are saved inside the `exports/` folder:
- **`exports/<exam_name>.txt`**: Clean, exact format:
  ```text
  1. বাংলাদেশের জাতীয় স্মৃতিসৌধ কোথায় অবস্থিত?
  A) ঢাকা
  B) সাভার
  C) গাজীপুর
  D) নারায়ণগঞ্জ
  Ans: B
  Exp: জাতীয় স্মৃতিসৌধ ঢাকার অদূরে সাভারে অবস্থিত।

  2. What is the full form of CPU?
  A) Central Processing Unit
  B) Central Performance Unit
  C) Computer Processing Unit
  D) Core Processing Unit
  Ans: A
  Exp: CPU stands for Central Processing Unit.
  ```
- **`exports/<exam_name>.json`**: Structured JSON containing all details.
- **`exports/<exam_name>.md`**: Formatted Markdown notes.
- **`exports/<exam_name>.csv`**: Spreadsheet format with individual columns for Question, Options A-E, Answer, and Explanation.

---

## 💡 Notes
- For **Asopori** exams, ensure the exam is publicly readable (free exam) and does not require a paid/premium student login.
- If you have an HTML file saved locally, you can also paste the local file path into the terminal!
