#!/usr/bin/env python3
"""Export Biddabari's 48th BCS MCQs in the requested plain-text format.

Run: python biddabari_scraper.py
Offline: python biddabari_scraper.py --html biddabari_source.html
Requires requests and beautifulsoup4 from requirements.txt.
Answers are copied from the source, not independently fact-checked.
"""

import argparse
import re
import sys
import unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://biddabari.com/bcs-question-bank/48th-bcs-question-solution-pdf"
DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
LETTERS = dict(zip("কখগঘ", "ABCD"))
QUESTION = re.compile(r"^([০-৯0-9]+)[.)।](?:\s+(.*)|$)")
OPTION = re.compile(r"^([কখগঘABCDabcd])[.)।:]\s*(.*)$")
ANSWER = re.compile(r"^(?:উত্তর|Answer|Ans)\s*[:：]\s*(.*)$", re.I)
EXPLANATION = re.compile(r"^(?:ব্যাখ্যা|Explanation|Exp)\s*[:：]\s*(.*)$", re.I)


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


def match_key(text):
    text = unicodedata.normalize("NFC", clean(text)).translate(DIGITS)
    return re.sub(r"[\s\u200b\u200c\u200d\ufeff]", "", text).casefold()


def extract_questions(html):
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one(".blog-slide-content")
    if content is None:
        raise ValueError("The article container was not found; the site layout may have changed.")
    for tag in content.select("script, style"):
        tag.decompose()
    # Keep mathematical superscripts/subscripts meaningful in plain text.
    for tag in content.select("sup, sub"):
        tag.replace_with(("^" if tag.name == "sup" else "_") + clean(tag.get_text()))
    questions = []
    current = None
    field = None
    for raw in content.get_text("\n", strip=True).splitlines():
        line = clean(raw)
        if not line:
            continue
        q = QUESTION.match(line)
        option = OPTION.match(line)
        answer = ANSWER.match(line)
        explanation = EXPLANATION.match(line)
        if q:
            if current:
                questions.append(current)
            current = {"number": int(q[1].translate(DIGITS)), "question": q[2] or "",
                       "options": {}, "answer": "", "explanation": ""}
            field = "question"
        elif current and option:
            letter = LETTERS.get(option[1], option[1].upper())
            if letter in current["options"]:
                raise ValueError(f"Duplicate option {letter} in question {current['number']}")
            current["options"][letter] = option[2]
            field = letter
        elif current and answer:
            current["answer"] = answer[1]
            field = "answer"
        elif current and explanation:
            current["explanation"] = explanation[1]
            field = "explanation"
        elif current and field:
            target = current["options"] if field in "ABCD" else current
            target[field] = clean(target[field] + " " + line)
    if current:
        questions.append(current)
    if not questions:
        raise ValueError("No questions found in the article.")
    seen = set()
    for item in questions:
        number = item["number"]
        if number in seen:
            raise ValueError(f"Duplicate question number: {number}")
        seen.add(number)
        if not item["question"] or set(item["options"]) != set("ABCD") or not all(item["options"].values()):
            raise ValueError(f"Question {number} has missing text or options.")
        matches = [letter for letter, value in item["options"].items()
                   if clean(value) == clean(item["answer"])]
        if not matches:
            matches = [letter for letter, value in item["options"].items()
                       if match_key(value) == match_key(item["answer"])]
        if len(matches) == 1:
            item["answer_letter"] = matches[0]
        else:
            label = item["answer"].strip(" ()[].।:")
            letter = LETTERS.get(label, label.upper())
            if letter not in item["options"]:
                raise ValueError(f"Cannot match answer for question {number}: {item['answer']!r}")
            item["answer_letter"] = letter
    return questions


def format_questions(questions):
    blocks = []
    for item in questions:
        lines = [f"{item['number']}. {item['question']}"]
        lines.extend(f"{letter}) {item['options'][letter]}" for letter in "ABCD")
        lines.append(f"Ans: {item['answer_letter']}")
        if item["explanation"]:
            lines.append("Exp: " + item["explanation"])
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, help="Read a saved HTML page instead of downloading")
    parser.add_argument("--output", type=Path, default=Path("exports/48th_bcs_biddabari.txt"))
    args = parser.parse_args()
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    try:
        if args.html:
            html = args.html.read_text(encoding="utf-8")
        else:
            response = requests.get(URL, timeout=(15, 60), headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            html = response.content.decode("utf-8-sig")
        questions = extract_questions(html)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(format_questions(questions), encoding="utf-8")
        print(f"Exported {len(questions)} questions to {args.output.resolve()}")
        present = {item["number"] for item in questions}
        missing = sorted(set(range(1, max(present) + 1)) - present)
        if missing:
            print("Question numbers absent from the source: " + ", ".join(map(str, missing)))
        print("Answers follow the source. Explanations are included only when available.")
    except (requests.RequestException, OSError, UnicodeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
