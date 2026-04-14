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
    '!': 'i', '+': 't', '#': 'h', '*': 'i'
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
    r'\b(people from \w+ are (stupid|inferior|useless|trash|bullshit))\b',
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
# ─── Harmful Intent Patterns ──────────────────────────────────
# Catches combination-based harmful sentences that BERT misses
HARMFUL_INTENT_PATTERNS = [

    # Weapons / explosives
    r'\b(how to|ways? to|steps? to|guide to|make|build|create|craft).{0,30}(bomb|explosive|grenade|weapon|gun|pistol|rifle)\b',
    r'\b(make|build|assemble).{0,20}(bomb|explosive|weapon)\b',

    # Poison / harm someone
    r'\b(how to|ways? to|best way to).{0,30}(poison|drug|sedate|kill|murder|harm|hurt).{0,20}(someone|a person|people|him|her|them)\b',
    r'\b(poison|drug).{0,20}(someone|quietly|secretly|without)\b',

    # Hacking / cybercrime
    r'\b(how to|ways? to).{0,30}(hack|crack|break into|access).{0,30}(account|instagram|facebook|email|system|password|phone)\b',
    r'\b(hack|steal).{0,20}(account|password|data|information)\b',

    # Physical break-in
    r'\b(how to|ways? to).{0,30}(break into|enter|sneak into|get into).{0,30}(house|home|building|room|car)\b',

    # Torture / violence instructions
    r'\b(how to|ways? to|steps? to).{0,30}(torture|hurt|harm|beat|attack|assault).{0,20}(someone|a person|him|her|them|people)\b',
    r'\b(torture|harm|hurt).{0,20}(without|no|leaving).{0,20}(marks?|trace|evidence|proof)\b',

    # Manipulation / blackmail
    r'\b(how to|ways? to).{0,30}(manipulate|blackmail|extort|threaten|control).{0,20}(someone|people|him|her|them)\b',
    r'\b(blackmail|extort).{0,20}(someone|online|person)\b',

    # Fake news / misinformation
    r'\b(how to|ways? to).{0,30}(spread|create|make).{0,20}(fake news|misinformation|propaganda|rumours?|lies)\b',

    # Disappear / evade law
    r'\b(how to|ways? to).{0,30}(disappear|hide|escape|evade).{0,20}(without|from|police|law|trace|being found)\b',

    # Destroy reputation / harass
    r'\b(how to|ways? to).{0,30}(destroy|ruin|damage).{0,20}(reputation|life|career|image)\b',

    # Eliminate / eradicate people
    r'\b(eliminate|eradicate|wipe out|get rid of).{0,20}(them|all|people|community|group|everyone)\b',
    r'\b(we should|let.s).{0,20}(eliminate|remove|get rid of|destroy).{0,20}(them|all|people|community)\b',

    # Self harm instruction
    r'\b(how to|ways? to).{0,30}(hurt yourself|harm yourself|self.harm|self.destruct)\b',
    r'\byou should (hurt|harm|kill) yourself\b',
]

def check_harmful_intent(text):
    lower = text.lower()
    for pattern in HARMFUL_INTENT_PATTERNS:
        if re.search(pattern, lower):
            return True
    return False

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
    # Step 2c — harmful intent / combination sentence check
    if check_harmful_intent(original):
        return jsonify({
            'allowed': False,
            'label': 'Harmful intent detected',
            'reason': 'Your caption contains language that describes or instructs harmful, dangerous, or illegal activity.',
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

    # Strict block 
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