#!/usr/bin/env python3
"""
MCQ Question & Answer Scraper
Extracts MCQ Questions, Options, Correct Answer, and Explanation from exam URLs.
Specially optimized for Asopori.com and general MCQ websites.
Outputs in clean format:
  1. Question text
  A) Option 1
  B) Option 2
  C) Option 3
  D) Option 4
  Ans: B
  Exp: Explanation (if available)
"""

import sys
import os
import re
import json
import csv
from urllib.parse import urlparse

# Set UTF-8 encoding for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import requests
from bs4 import BeautifulSoup

try:
    import colorama
    from colorama import Fore, Style
    colorama.init(autoreset=True)
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False
    class Fore:
        GREEN = BLUE = CYAN = YELLOW = RED = MAGENTA = WHITE = RESET = ""
    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ""


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

OPTION_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F']


def clean_url(raw_input: str) -> str:
    """Cleans up link input (e.g. view-source: prefix, quotes, spaces)."""
    cleaned = raw_input.strip().strip("'\"`")
    if cleaned.lower().startswith("view-source:"):
        cleaned = cleaned[12:].strip()
    return cleaned


def clean_option_text(text: str) -> str:
    """Removes duplicate prefixes like '(a)', 'a)', '[a]', 'ক)', '(ক)', '1.', etc."""
    cleaned = text.strip()
    # Strip any leading letter or numbering like a), (a), A., 1., [a], (১), etc.
    cleaned = re.sub(r'^(?:[\(\[]?[a-eA-Eক-ঙ1-5১-৫][\)\.\:\]]\s*)+', '', cleaned).strip()
    return cleaned


def extract_answer_letter(raw_answer: str, options: list[str], correct_key: str = "") -> str:
    """
    Extracts A, B, C, D... letter for the answer.
    Checks:
    1. correct_key (e.g. 'option_1' -> 'A', 'option_2' -> 'B', etc.)
    2. raw_answer starting with a letter/digit (e.g. '(d) brave' -> 'D', 'B' -> 'B', 'ক' -> 'A')
    3. matching text with options
    """
    letters = OPTION_LETTERS
    bengali_letters = {'ক': 'A', 'খ': 'B', 'গ': 'C', 'ঘ': 'D', 'ঙ': 'E'}
    
    # 1. From correct_key like "option_2"
    if correct_key:
        m = re.search(r'option_(\d+)', correct_key)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(letters):
                return letters[idx]

    clean_ans = raw_answer.strip()
    # Remove leading 'Answer:' or 'উত্তর:'
    clean_ans = re.sub(r'^(?:Answer|Ans|উত্তর)\s*[:\-]?\s*', '', clean_ans, flags=re.I).strip()

    # 2. Check if answer starts with a letter like "(b)", "b)", "[b]", "b", "B", "(খ)"
    m = re.match(r'^[\(\[]?([a-eA-Eক-ঙ])[\)\.\:\]]?\b', clean_ans)
    if m:
        char = m.group(1).upper()
        if char in letters:
            return char
        if char in bengali_letters:
            return bengali_letters[char]

    # Check numeric like "1", "2"
    m_num = re.match(r'^[\(\[]?([1-5১-৫])[\)\.\:\]]?\b', clean_ans)
    if m_num:
        val = m_num.group(1)
        num_map = {'1': 0, '2': 1, '3': 2, '4': 3, '5': 4, '১': 0, '২': 1, '৩': 2, '৪': 3, '৫': 4}
        if val in num_map and num_map[val] < len(letters):
            return letters[num_map[val]]

    # 3. Match answer text against cleaned option texts
    ans_body = clean_option_text(clean_ans).lower()
    if ans_body:
        for idx, opt in enumerate(options):
            opt_body = clean_option_text(opt).lower()
            if opt_body and (ans_body == opt_body or opt_body in ans_body or ans_body in opt_body):
                if idx < len(letters):
                    return letters[idx]

    # If it is already just a single letter A-E
    if clean_ans.upper() in letters:
        return clean_ans.upper()

    return clean_ans


def fetch_html(url_or_path: str) -> tuple[str, str]:
    """
    Fetches HTML content from URL or local file path.
    Returns (html_content, final_url_or_title).
    """
    if os.path.exists(url_or_path):
        with open(url_or_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read(), os.path.basename(url_or_path)

    target_url = url_or_path

    # Asopori specific URL adjustment:
    parsed = urlparse(target_url)
    if "asopori.com" in parsed.netloc.lower() and "/exam/" in parsed.path:
        if not parsed.path.rstrip("/").endswith("/read") and not parsed.path.rstrip("/").endswith("/leaderboard"):
            target_url = target_url.rstrip("/") + "/read"

    response = requests.get(target_url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or 'utf-8'
    return response.text, target_url


def parse_asopori(soup: BeautifulSoup, page_url: str) -> dict:
    """Specialized high-accuracy parser for Asopori exams."""
    h1 = soup.find('h1')
    title = h1.get_text(strip=True) if h1 else ""
    if not title and soup.title:
        title = soup.title.get_text(strip=True)
        title = re.sub(r'^(Reading Mode\s*-\s*|Asopori\s*-\s*)', '', title, flags=re.I).strip()

    questions = []

    # Asopori reading mode uses wire:key="q-<id>" containers
    q_containers = soup.find_all('div', attrs={'wire:key': lambda v: v and v.startswith('q-')})

    if not q_containers:
        article = soup.find('article')
        if article:
            q_containers = article.find_all('div', recursive=False)

    for idx, container in enumerate(q_containers, start=1):
        # 1. Question Title & Number
        h3 = container.find('h3')
        q_num = str(idx)
        q_text = ""

        if h3:
            spans = h3.find_all('span')
            if len(spans) >= 2:
                q_num = spans[0].get_text(strip=True).rstrip('.')
                q_text = spans[1].get_text(strip=True)
            else:
                raw_h3 = h3.get_text(' ', strip=True)
                match = re.match(r'^([\d০-৯]+)[\.\)]\s*(.*)', raw_h3)
                if match:
                    q_num, q_text = match.group(1), match.group(2)
                else:
                    q_text = raw_h3

        # 2. Options
        raw_options = []
        opt_div = container.find('div', class_=lambda c: c and 'space-y-2' in c)
        opt_elements = opt_div.find_all('p') if opt_div else container.find_all('p')
        for p in opt_elements:
            text = p.get_text(' ', strip=True)
            if re.match(r'^(?:[a-eA-Eক-ঙ]|[1-5১-৫])[\)\.]\s+', text):
                raw_options.append(text)

        # 3. Answer
        raw_answer = ""
        for p in container.find_all('p'):
            t = p.get_text(' ', strip=True)
            if re.search(r'^(Answer|উত্তর)\s*:', t, re.I):
                raw_answer = re.sub(r'^(Answer|উত্তর)\s*:\s*', '', t, flags=re.I).strip()
                break

        # 4. Explanation
        explanation = ""
        for p in container.find_all(['p', 'div']):
            t = p.get_text(' ', strip=True)
            if re.search(r'^(Explanation|ব্যাখ্যা)\s*:', t, re.I):
                explanation = re.sub(r'^(Explanation|ব্যাখ্যা)\s*:\s*', '', t, flags=re.I).strip()
                break

        # 5. Check Alpine.js report error button for backup/exact data
        correct_key = ""
        report_btn = container.find('button', attrs={'x-on:click': lambda v: v and 'form' in v})
        if report_btn:
            click_attr = report_btn.get('x-on:click', '')
            match = re.search(r'form\s*=\s*(\{.*?\});', click_attr)
            if match:
                try:
                    data = json.loads(match.group(1))
                    if not q_text and data.get('q_text'):
                        q_text = data['q_text']
                    if not raw_options and data.get('o1'):
                        raw_options = [data.get('o1', ''), data.get('o2', ''), data.get('o3', ''), data.get('o4', '')]
                    if not explanation and data.get('explanation'):
                        explanation = data['explanation'].strip()
                    correct_key = data.get('correct', '')
                except Exception:
                    pass

        if not q_text:
            continue

        # Format options with clean letter A), B), C), D)
        formatted_options = []
        for i, opt in enumerate(raw_options):
            clean_body = clean_option_text(opt)
            letter = OPTION_LETTERS[i] if i < len(OPTION_LETTERS) else f"Opt{i+1}"
            formatted_options.append(f"{letter}) {clean_body}")

        # Extract answer letter (e.g. 'A', 'B', 'C', 'D')
        ans_letter = extract_answer_letter(raw_answer, raw_options, correct_key)

        questions.append({
            "number": q_num,
            "question": q_text,
            "options": formatted_options,
            "answer": ans_letter,
            "raw_answer": raw_answer,
            "explanation": explanation
        })

    return {
        "title": title or "Asopori Exam",
        "url": page_url,
        "total_questions": len(questions),
        "questions": questions
    }


def parse_generic_mcq(soup: BeautifulSoup, page_url: str) -> dict:
    """Universal fallback parser for general MCQ websites."""
    title = soup.find('h1')
    title_text = title.get_text(strip=True) if title else (soup.title.get_text(strip=True) if soup.title else "MCQ Exam")

    questions = []

    candidates = soup.find_all(
        lambda tag: tag.name in ['div', 'article', 'li', 'section'] and
        any(c in " ".join(tag.get('class', [])).lower() for c in ['question-item', 'mcq-item', 'single-question', 'question_item', 'ques-box', 'wp-block-group'])
    )

    if not candidates:
        headers = soup.find_all(['h2', 'h3', 'h4', 'p', 'b', 'strong'])
        for h in headers:
            text = h.get_text(' ', strip=True)
            if re.match(r'^(?:Q(?:uestion)?\.?\s*)?[\d০-৯]+[\.\)]\s+', text):
                parent = h.parent
                if parent not in candidates and parent.name in ['div', 'li', 'article', 'section']:
                    candidates.append(parent)

    for idx, c in enumerate(candidates, start=1):
        all_text = c.get_text('\n', strip=True).split('\n')
        all_text = [t.strip() for t in all_text if t.strip()]

        q_text = ""
        raw_options = []
        raw_answer = ""
        explanation = ""

        for line in all_text:
            if re.match(r'^(?:Q(?:uestion)?\.?\s*)?[\d০-৯]+[\.\)]\s+', line):
                q_text = re.sub(r'^(?:Q(?:uestion)?\.?\s*)?[\d০-৯]+[\.\)]\s*', '', line)
                break
        if not q_text and all_text:
            q_text = all_text[0]

        for line in all_text:
            if re.match(r'^(?:[a-eA-Eক-ঙ]|[1-5১-৫])[\)\.]\s+', line):
                raw_options.append(line)

        for line in all_text:
            if re.search(r'^(?:Answer|Correct Answer|Ans|উত্তর)\s*[:\-]', line, re.I):
                raw_answer = re.sub(r'^(?:Answer|Correct Answer|Ans|উত্তর)\s*[:\-]\s*', '', line, flags=re.I).strip()
                break

        for line in all_text:
            if re.search(r'^(?:Explanation|Explain|Solution|ব্যাখ্যা)\s*[:\-]', line, re.I):
                explanation = re.sub(r'^(?:Explanation|Explain|Solution|ব্যাখ্যা)\s*[:\-]\s*', '', line, flags=re.I).strip()
                break

        if q_text and (raw_options or raw_answer):
            formatted_options = []
            for i, opt in enumerate(raw_options):
                clean_body = clean_option_text(opt)
                letter = OPTION_LETTERS[i] if i < len(OPTION_LETTERS) else f"Opt{i+1}"
                formatted_options.append(f"{letter}) {clean_body}")

            ans_letter = extract_answer_letter(raw_answer, raw_options)

            questions.append({
                "number": str(idx),
                "question": q_text,
                "options": formatted_options,
                "answer": ans_letter,
                "raw_answer": raw_answer,
                "explanation": explanation
            })

    return {
        "title": title_text,
        "url": page_url,
        "total_questions": len(questions),
        "questions": questions
    }


def parse_page(html: str, url: str) -> dict:
    """Determines parser and parses the page."""
    soup = BeautifulSoup(html, 'html.parser')
    if "asopori.com" in url.lower() or soup.find(attrs={'wire:key': lambda v: v and v.startswith('q-')}):
        result = parse_asopori(soup, url)
        if result["total_questions"] > 0:
            return result
    generic_res = parse_generic_mcq(soup, url)
    if generic_res["total_questions"] > 0:
        return generic_res
    return parse_asopori(soup, url)


def display_results(data: dict):
    """Displays questions, options, answer, and explanation nicely in terminal."""
    print()
    print(f"{Fore.CYAN}{Style.BRIGHT}{'=' * 70}")
    print(f"{Fore.YELLOW}{Style.BRIGHT}  EXAM: {data['title']}")
    print(f"{Fore.WHITE}  SOURCE: {data['url']}")
    print(f"{Fore.GREEN}  TOTAL QUESTIONS: {data['total_questions']}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'=' * 70}{Style.RESET_ALL}\n")

    if data['total_questions'] == 0:
        print(f"{Fore.RED}[!] No MCQ questions could be extracted from this page.")
        print(f"{Fore.YELLOW}Tip: If this is an Asopori exam, make sure it is not a locked/premium exam that requires student login.{Style.RESET_ALL}\n")
        return

    for item in data['questions']:
        print(f"{Fore.CYAN}{Style.BRIGHT}{item['number']}. {item['question']}{Style.RESET_ALL}")
        for opt in item['options']:
            print(f"{Fore.WHITE}{opt}")
        if item['answer']:
            print(f"{Fore.GREEN}{Style.BRIGHT}Ans: {item['answer']}{Style.RESET_ALL}")
        if item['explanation']:
            print(f"{Fore.MAGENTA}Exp: {item['explanation']}{Style.RESET_ALL}")
        print()


def sanitize_filename(name: str) -> str:
    """Removes invalid characters from filename."""
    s = re.sub(r'[\/:*?"<>|]', '_', name)
    s = re.sub(r'\s+', '_', s).strip('._')
    return s[:60] if s else "mcq_exam"


def export_files(data: dict, output_dir: str = "exports") -> dict:
    """Exports data into TXT (requested format), JSON, MD, and CSV files."""
    if data['total_questions'] == 0:
        return {}

    os.makedirs(output_dir, exist_ok=True)
    base_name = sanitize_filename(data['title'])
    
    txt_path = os.path.join(output_dir, f"{base_name}.txt")
    json_path = os.path.join(output_dir, f"{base_name}.json")
    md_path = os.path.join(output_dir, f"{base_name}.md")
    csv_path = os.path.join(output_dir, f"{base_name}.csv")

    # 1. TXT Export - Exact requested format
    with open(txt_path, 'w', encoding='utf-8') as f:
        for i, q in enumerate(data['questions']):
            f.write(f"{q['number']}. {q['question']}\n")
            for opt in q['options']:
                f.write(f"{opt}\n")
            if q['answer']:
                f.write(f"Ans: {q['answer']}\n")
            if q['explanation']:
                f.write(f"Exp: {q['explanation']}\n")
            
            # Add a single empty line between questions, but not after the last one
            if i < len(data['questions']) - 1:
                f.write("\n")

    # 2. JSON Export
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 3. Markdown Export
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# {data['title']}\n\n")
        f.write(f"- **Source:** {data['url']}\n")
        f.write(f"- **Total Questions:** {data['total_questions']}\n\n---\n\n")
        for q in data['questions']:
            f.write(f"### {q['number']}. {q['question']}\n\n")
            for opt in q['options']:
                f.write(f"- {opt}\n")
            if q['answer']:
                f.write(f"\n**Ans:** `{q['answer']}`\n")
            if q['explanation']:
                f.write(f"\n> **Exp:** {q['explanation']}\n")
            f.write("\n---\n\n")

    # 4. CSV Export
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["No", "Question", "Option A", "Option B", "Option C", "Option D", "Option E", "Answer", "Explanation"])
        for q in data['questions']:
            row = [q['number'], q['question']]
            opts = [clean_option_text(o) for o in q['options']] + [""] * 5
            row.extend(opts[:5])
            row.append(q['answer'])
            row.append(q['explanation'])
            writer.writerow(row)

    return {
        "txt": txt_path,
        "json": json_path,
        "md": md_path,
        "csv": csv_path
    }


def process_link(raw_link: str):
    """Processes a single URL or file path."""
    link = clean_url(raw_link)
    if not link:
        print(f"{Fore.RED}Please provide a valid link or file path.{Style.RESET_ALL}")
        return

    print(f"\n{Fore.CYAN}Fetching page source from:{Style.RESET_ALL} {link}")
    try:
        html, actual_url = fetch_html(link)
    except requests.RequestException as e:
        print(f"{Fore.RED}[Error fetching page]: {e}{Style.RESET_ALL}")
        return
    except Exception as e:
        print(f"{Fore.RED}[Error]: {e}{Style.RESET_ALL}")
        return

    print(f"{Fore.GREEN}Parsing MCQ questions, options, answers, and explanations...{Style.RESET_ALL}")
    data = parse_page(html, actual_url)
    display_results(data)

    if data['total_questions'] > 0:
        saved_files = export_files(data)
        print(f"{Fore.GREEN}{Style.BRIGHT}[✓] Successfully saved all questions to files:{Style.RESET_ALL}")
        for fmt, path in saved_files.items():
            print(f"  • {fmt.upper()}: {Fore.CYAN}{os.path.abspath(path)}{Style.RESET_ALL}")
        print()


def print_banner():
    banner = f"""
{Fore.CYAN}{Style.BRIGHT}======================================================================
     🎓 MCQ QUESTION & ANSWER EXTRACTOR (ASOPORI & GENERAL)
======================================================================
  Paste any exam link (e.g., https://asopori.com/exam/... or view-source:...)
  The script extracts: Question text, Options, Correct Answer, Explanation
======================================================================{Style.RESET_ALL}
"""
    print(banner)


def main():
    print_banner()

    if len(sys.argv) > 1:
        target_link = " ".join(sys.argv[1:])
        process_link(target_link)
        return

    while True:
        try:
            user_input = input(f"{Fore.YELLOW}{Style.BRIGHT}Enter MCQ Link (or type 'q' / 'exit' to quit): {Style.RESET_ALL}").strip()
            if not user_input:
                continue
            if user_input.lower() in ['q', 'quit', 'exit']:
                print(f"{Fore.GREEN}Exiting. Have a great day!{Style.RESET_ALL}")
                break

            process_link(user_input)

        except (KeyboardInterrupt, EOFError):
            print(f"\n{Fore.GREEN}Session terminated. Goodbye!{Style.RESET_ALL}")
            break


if __name__ == "__main__":
    main()
