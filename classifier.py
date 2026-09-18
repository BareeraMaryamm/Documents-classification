import ollama
import sys
import re

# ---------------------------------------------------------------------------
# Simple ANSI color helpers (no extra dependencies needed)
# ---------------------------------------------------------------------------
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"
    BLUE = "\033[34m"


def color(text, *codes):
    return f"{''.join(codes)}{text}{C.RESET}"


VALID_CATEGORIES = ["Technology", "Sports", "Education", "Business"]

CATEGORY_COLORS = {
    "Technology": C.BLUE,
    "Sports": C.GREEN,
    "Education": C.YELLOW,
    "Business": C.MAGENTA,
}


def print_banner():
    width = 56
    title = "A I   T E X T   C L A S S I F I E R"   # letter-spaced for a "display font" look
    subtitle = "~ Ollama + Python ~"
    print(color("╭" + "─" * (width - 2) + "╮", C.CYAN, C.BOLD))
    print(color("│", C.CYAN, C.BOLD) + color(title.center(width - 2), C.CYAN, C.BOLD) + color("│", C.CYAN, C.BOLD))
    print(color("│", C.CYAN, C.BOLD) + color(subtitle.center(width - 2), C.YELLOW, C.BOLD) + color("│", C.CYAN, C.BOLD))
    print(color("╰" + "─" * (width - 2) + "╯", C.CYAN, C.BOLD))
    print()
    print(color("Categories: ", C.DIM) + color("Technology", C.BLUE) + " | " +
          color("Sports", C.GREEN) + " | " + color("Education", C.YELLOW) + " | " +
          color("Business", C.MAGENTA))
    print(color("Type 'exit' or 'quit' to stop.\n", C.DIM))


CATEGORY_EXPLANATIONS = {
    "Technology": "Related to gadgets, software, AI, the internet, or scientific innovation.",
    "Sports": "Related to games, athletes, tournaments, or physical competitions.",
    "Education": "Related to schools, universities, learning, students, or courses.",
    "Business": "Related to companies, finance, markets, trade, or the economy.",
}


def print_mode_menu():
    print(color("Choose classification mode:", C.BOLD))
    print(f"  {color('1', C.CYAN, C.BOLD)} - Single category  (e.g. Technology)")
    print(f"  {color('2', C.CYAN, C.BOLD)} - Multi-label with confidence    (e.g. Technology - 70%, Business - 30%)")


def choose_mode():
    print_mode_menu()
    while True:
        choice = input(color("\nEnter 1 or 2: ", C.CYAN)).strip()
        if choice in ("1", "2"):
            return choice
        print(color("✗ Please enter 1 or 2.", C.RED))


# ---------------------------------------------------------------------------
# Core classification logic - Mode 1: Single category
# ---------------------------------------------------------------------------
def classify_single(text):
    """
    Classify the given text into exactly one category:
    Technology, Sports, Education, or Business.
    Returns ONLY the category name (no explanation).
    """
    system_instruction = (
        "You are a text classification system. "
        "Classify the given text into exactly ONE of these categories: "
        "Technology, Sports, Education, or Business. "
        "Only respond with the single category name, nothing else. "
        "Do not explain your reasoning. Do not add punctuation, quotes, or extra words."
    )

    try:
        response = ollama.chat(
            model="llama3.1",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": text.strip()},
            ],
            options={"temperature": 0.0, "num_predict": 10},
        )

        label = response["message"]["content"].strip()
        label = label.replace(".", "").replace('"', "").replace("'", "").strip()
        label = label.split("\n")[0].split()[0] if label else label

        for category in VALID_CATEGORIES:
            if category.lower() == label.lower():
                return category

        return label if label else "Unknown"

    except ollama.ResponseError as e:
        return f"Error: Ollama response error - {e}"
    except Exception as e:
        return f"Error: Ensure Ollama service is running. Details: {e}"


# ---------------------------------------------------------------------------
# Bonus - Mode 2: Multi-label classification with confidence scores
# ---------------------------------------------------------------------------
def classify_multi(text):
    """
    Classify the given text into one or more categories with confidence
    percentages that add up to 100%.
    Returns a list of (category, confidence) tuples, sorted highest first.
    """
    system_instruction = (
        "You are a text classification system. "
        "Analyze the given text and assign confidence percentages across these "
        "categories: Technology, Sports, Education, Business. "
        "Only include categories that are actually relevant (skip ones with 0% relevance). "
        "The percentages must add up to 100. "
        "Respond ONLY in this exact format, one category per line, nothing else:\n"
        "Category - XX%\n"
        "Example:\n"
        "Technology - 70%\n"
        "Business - 30%"
    )

    try:
        response = ollama.chat(
            model="llama3.1",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": text.strip()},
            ],
            options={"temperature": 0.0, "num_predict": 60},
        )

        raw = response["message"]["content"].strip()
        results = []

        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            match = re.match(r"([A-Za-z]+)\s*[-:]\s*(\d{1,3})\s*%?", line)
            if match:
                cat_raw, pct_raw = match.group(1), match.group(2)
                for category in VALID_CATEGORIES:
                    if category.lower() == cat_raw.lower():
                        results.append((category, int(pct_raw)))
                        break

        results.sort(key=lambda x: x[1], reverse=True)
        return results if results else [("Unknown", 100)]

    except ollama.ResponseError as e:
        return [(f"Error: Ollama response error - {e}", 0)]
    except Exception as e:
        return [(f"Error: Ensure Ollama service is running. Details: {e}", 0)]


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------
def print_single_result(label):
    print()
    if label.startswith("Error:"):
        print(color(f"✗ {label}", C.RED, C.BOLD))
    elif label in CATEGORY_COLORS:
        cat_color = CATEGORY_COLORS[label]
        print(color("┌" + "─" * 40 + "┐", cat_color))
        print(color("│ ", cat_color) + color("CATEGORY: ", C.BOLD) +
              color(label, cat_color, C.BOLD) +
              " " * (40 - 12 - len(label)) + color("│", cat_color))
        print(color("└" + "─" * 40 + "┘", cat_color))
    else:
        print(color(f"⚠ Unexpected output: {label}", C.YELLOW, C.BOLD))
    print()


def print_multi_result(results):
    print()
    if results and results[0][0].startswith("Error:"):
        print(color(f"✗ {results[0][0]}", C.RED, C.BOLD))
        print()
        return

    width = 44
    print(color("┌" + "─" * width + "┐", C.CYAN))
    print(color("│ ", C.CYAN) + color("MULTI-LABEL CLASSIFICATION", C.BOLD) +
          " " * (width - 2 - len("MULTI-LABEL CLASSIFICATION")) + color("│", C.CYAN))
    print(color("├" + "─" * width + "┤", C.CYAN))

    for category, pct in results:
        cat_color = CATEGORY_COLORS.get(category, C.RESET)
        bar_len = int(pct / 5)  # scale to 20 chars max
        bar = "█" * bar_len + "░" * (20 - bar_len)
        line = f"{category:<12} {color(bar, cat_color)} {pct:>3}%"
        visible_len = 12 + 1 + 20 + 1 + 4  # approx visible width ignoring color codes
        pad = max(0, width - 2 - visible_len)
        print(color("│ ", C.CYAN) + line + " " * pad + color(" │", C.CYAN))

    print(color("└" + "─" * width + "┘", C.CYAN))

    # Explain what each returned category actually means
    print(color("\nWhat these categories mean:", C.DIM))
    for category, pct in results:
        explanation = CATEGORY_EXPLANATIONS.get(category, "No explanation available.")
        cat_color = CATEGORY_COLORS.get(category, C.RESET)
        print(f"  {color('•', cat_color)} {color(category, cat_color, C.BOLD)}: {color(explanation, C.DIM)}")
    print()


# ---------------------------------------------------------------------------
# Script logic - runs continuously in a loop (no main() wrapper)
# ---------------------------------------------------------------------------
print_banner()
mode = choose_mode()
mode_name = "Single category" if mode == "1" else "Multi-label with confidence"
print(color(f"\n✓ Mode set to: {mode_name}", C.GREEN, C.BOLD))
print(color("(Type 'mode' anytime to switch, 'exit' or 'quit' to stop.)\n", C.DIM))

while True:
    try:
        user_input = input(color("Enter text to classify: ", C.CYAN, C.BOLD))
    except EOFError:
        break

    stripped = user_input.strip().lower()

    if stripped in ("exit", "quit"):
        print(color("\nGoodbye!", C.DIM))
        break

    if stripped == "mode":
        print()
        mode = choose_mode()
        mode_name = "Single category" if mode == "1" else "Multi-label with confidence"
        print(color(f"\n✓ Mode switched to: {mode_name}\n", C.GREEN, C.BOLD))
        continue

    if not user_input.strip():
        print(color("✗ Please enter some text.\n", C.RED))
        continue

    if mode == "1":
        label = classify_single(user_input)
        print_single_result(label)
    else:
        results = classify_multi(user_input)
        print_multi_result(results)