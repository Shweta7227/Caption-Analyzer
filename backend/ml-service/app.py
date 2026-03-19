from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import pipeline
import re

app = Flask(__name__)
CORS(app)

print("Loading ML model, please wait...")
classifier = pipeline(
    "text-classification",
    model="unitary/toxic-bert",
    top_k=None
)
print("Model ready!")

# ─── Text Normalizer ──────────────────────────────────────────
# Handles leet speak, spaced letters, special char substitutions
LEET_MAP = {
    '0': 'o', '1': 'i', '3': 'e', '4': 'a',
    '5': 's', '7': 't', '@': 'a', '$': 's',
    '!': 'i', '+': 't', '#': 'h'
}

def normalize(text):
    # Remove spaces between single letters: "i d i o t" → "idiot"
    text = re.sub(r'\b(\w)\s(\w)\s(\w)\s(\w)\s(\w)\b', lambda m: ''.join(m.groups()), text)
    text = re.sub(r'\b(\w)\s(\w)\s(\w)\s(\w)\b', lambda m: ''.join(m.groups()), text)
    # Replace leet characters
    result = ''
    for ch in text:
        result += LEET_MAP.get(ch, ch)
    # Remove special chars used to mask: id!ot → idiot, d*mb → dumb
    result = re.sub(r'[*!@#$%]', '', result)
    return result.lower()

# ─── Hate Speech Keyword Patterns ─────────────────────────────
HATE_PATTERNS = [
    # religion
    r'\b(i hate (all )?(muslims?|hindus?|christians?|sikhs?|jews?|buddhists?))\b',
    r'\b((muslims?|hindus?|christians?|sikhs?|jews?) (are|should) (stupid|die|not exist|inferior|trash))\b',
    # caste
    r'\b(i hate (all )?\w+ caste)\b',
    r'\b(\w+ caste (are|is) (inferior|trash|stupid|useless))\b',
    # gender
    r'\b(all (women|men|girls|boys|females|males) are (stupid|useless|inferior|trash|worthless))\b',
    r'\b(women (should|must) (not|stay|shut))\b',
    # nationality
    r'\bgo back to (your country|where you came from)\b',
    r'\b(people from \w+ are (stupid|inferior|useless|trash))\b',
    r'\b(they should not exist)\b',
    r'\b(those people are inferior)\b',
]

# ─── Sarcasm / Hidden Toxicity Patterns ───────────────────────
SARCASM_PATTERNS = [
    r'\bgreat job ruining\b',
    r'\bwow.{0,20}(genius|smart|brilliant).{0,10}(🙄|/s|seriously|\.\.\.)?\b',
    r'\bclap for yourself\b',
    r'\boutdid yourself.{0,20}(wrong|fail|terrible|bad)\b',
    r'\bsuch a (genius|hero|winner).{0,10}(🙄|not|right)\b',
]
# ─── Blocked Emojis ───────────────────────────────────────────
BLOCKED_EMOJIS = {
    '🖕': 'offensive gesture',
    '🔪': 'violent content',
    '💣': 'violent content',
    '☠️': 'threatening content',
    '🤬': 'extreme aggression',
    '👊': 'violent content',
    '🪓': 'violent content',
    '🔫': 'violent content',
    '💢': 'aggressive content',
    '🗡️': 'violent content',
    '⚔️': 'violent content',
    '🧨': 'violent content',
    '💩': 'offensive content',
    '😡': 'extreme anger and aggression',
    '🚬': 'promotion of smoking or substance use',
    '🍗': 'content that may offend religious sentiments',
    '🍖': 'content that may offend religious sentiments',
    '🥩': 'content that may offend religious sentiments',
    '🍤': 'content that may offend religious sentiments',
    '🍾': 'promotion of alcohol',
    '🍷': 'promotion of alcohol',
}

def check_blocked_emojis(text):
    for emoji, reason in BLOCKED_EMOJIS.items():
        if emoji in text:
            return True, emoji, reason
    return False, None, None

def check_hate_speech(text):
    lower = text.lower()
    for pattern in HATE_PATTERNS:
        if re.search(pattern, lower):
            return True
    return False

def check_sarcasm(text):
    lower = text.lower()
    for pattern in SARCASM_PATTERNS:
        if re.search(pattern, lower):
            return True
    return False

# ─── Main Analyze Route ───────────────────────────────────────
@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    original = data.get('caption', '')

    if not original.strip():
        return jsonify({ 'allowed': False, 'reason': 'Caption is empty.', 'label': 'Empty input', 'severity': 'block' })

    # Step 1 — normalize to catch masked abuse
    cleaned = normalize(original)
    print(f"\nOriginal : '{original}'")
    print(f"Normalized: '{cleaned}'")

    # Step 2 — rule-based checks first (fast)
    if check_hate_speech(original):
        return jsonify({
            'allowed': False,
            'label': 'Hate speech',
            'reason': 'Your caption contains hate speech targeting a religion, caste, gender, or nationality.',
            'severity': 'block'
        })

    if check_sarcasm(original):
        return jsonify({
            'allowed': False,
            'label': 'Hidden toxicity',
            'reason': 'Your caption appears to contain sarcastic or passive-aggressive harmful content.',
            'severity': 'warn'
        })
    # Step 2b — check for blocked emojis
    emoji_blocked, found_emoji, emoji_reason = check_blocked_emojis(original)
    if emoji_blocked:
        return jsonify({
            'allowed': False,
            'label': 'Inappropriate emoji',
            'reason': f'Your caption contains an emoji ({found_emoji}) that signals {emoji_reason}.',
            'severity': 'block'
        })

    # Step 3 — run ML model on normalized text
    results = classifier(cleaned)[0]
    scores = { r['label'].lower(): round(r['score'], 4) for r in results }
    print(f"Scores    : {scores}\n")

    severe  = scores.get('severe_toxic', 0)
    threat  = scores.get('threat', 0)
    obscene = scores.get('obscene', 0)
    insult  = scores.get('insult', 0)
    hate    = scores.get('identity_hate', 0)
    toxic   = scores.get('toxic', 0)

    # Strict block — high severity
    if severe > 0.4:
        return jsonify({ 'allowed': False, 'label': 'Severely toxic', 'reason': 'Your caption contains severely toxic content.', 'severity': 'block', 'scores': scores })
    if threat > 0.4:
        return jsonify({ 'allowed': False, 'label': 'Threatening content', 'reason': 'Your caption contains threatening or violent language.', 'severity': 'block', 'scores': scores })
    if hate > 0.4:
        return jsonify({ 'allowed': False, 'label': 'Hate speech', 'reason': 'Your caption contains hate speech targeting a group.', 'severity': 'block', 'scores': scores })

    # Medium block
    if obscene > 0.5:
        return jsonify({ 'allowed': False, 'label': 'Obscene content', 'reason': 'Your caption contains obscene or explicit content.', 'severity': 'block', 'scores': scores })
    if insult > 0.5:
        return jsonify({ 'allowed': False, 'label': 'Insulting language', 'reason': 'Your caption contains insulting language toward others.', 'severity': 'block', 'scores': scores })
    if toxic > 0.6:
        return jsonify({ 'allowed': False, 'label': 'Toxic content', 'reason': 'Your caption was detected as toxic or harmful.', 'severity': 'warn', 'scores': scores })

    # Mildly negative — ALLOW (don't block "this is bad work", "I disagree")
    return jsonify({ 'allowed': True, 'scores': scores })


if __name__ == '__main__':
    app.run(port=8080, debug=False)