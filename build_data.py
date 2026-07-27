import html
import json
import os
import re
import urllib.request

try:
    from pykakasi import kakasi
except ImportError:
    kakasi = None

JLPT_LEVELS = ["n5", "n4", "n3", "n2", "n1"]

KANJI_BASE = "https://raw.githubusercontent.com/evanclan/OpenJLPT/main/data/json/kanji"
VOCAB_BASE = "https://raw.githubusercontent.com/evanclan/OpenJLPT/main/data/json/vocab"
GRAMMAR_URL = "https://raw.githubusercontent.com/qatoqat/jlpt-grammar/main/grammar-data.json"

PRIMARY_MEANING_OVERRIDES_N5 = {
    "校": "school",
    "本": "book",
    "円": "yen",
    "話": "speak",
    "聞": "listen",
    "見": "see",
    "行": "go",
    "来": "come",
    "上": "up",
    "下": "down",
    "中": "middle",
    "前": "before",
    "後": "after",
    "大": "big",
    "小": "small",
    "長": "long",
}

MEANING_BAD_HINTS = [
    "radical",
    "sign of",
    "chinese zodiac",
    "printing",
    "proof",
    "correction",
    "counter for",
    "or three-stroke",
    "turkey",
    "spain",
]

UNSAFE_EN_PATTERNS = [
    re.compile(r"\bgo to hell\b", re.I),
    re.compile(r"\bshut up\b", re.I),
    re.compile(r"\bidiot\b", re.I),
    re.compile(r"\bdamn\b", re.I),
]

UNSAFE_JP_PATTERNS = [
    re.compile(r"行け[！!]?$"),
]

HIRAGANA_ROWS = [
    [("あ", "a"), ("い", "i"), ("う", "u"), ("え", "e"), ("お", "o")],
    [("か", "ka"), ("き", "ki"), ("く", "ku"), ("け", "ke"), ("こ", "ko")],
    [("さ", "sa"), ("し", "shi"), ("す", "su"), ("せ", "se"), ("そ", "so")],
    [("た", "ta"), ("ち", "chi"), ("つ", "tsu"), ("て", "te"), ("と", "to")],
    [("な", "na"), ("に", "ni"), ("ぬ", "nu"), ("ね", "ne"), ("の", "no")],
    [("は", "ha"), ("ひ", "hi"), ("ふ", "fu"), ("へ", "he"), ("ほ", "ho")],
    [("ま", "ma"), ("み", "mi"), ("む", "mu"), ("め", "me"), ("も", "mo")],
    [("や", "ya"), ("ゆ", "yu"), ("よ", "yo")],
    [("ら", "ra"), ("り", "ri"), ("る", "ru"), ("れ", "re"), ("ろ", "ro")],
    [("わ", "wa"), ("を", "wo"), ("ん", "n")],
]

KATAKANA_ROWS = [
    [("ア", "a"), ("イ", "i"), ("ウ", "u"), ("エ", "e"), ("オ", "o")],
    [("カ", "ka"), ("キ", "ki"), ("ク", "ku"), ("ケ", "ke"), ("コ", "ko")],
    [("サ", "sa"), ("シ", "shi"), ("ス", "su"), ("セ", "se"), ("ソ", "so")],
    [("タ", "ta"), ("チ", "chi"), ("ツ", "tsu"), ("テ", "te"), ("ト", "to")],
    [("ナ", "na"), ("ニ", "ni"), ("ヌ", "nu"), ("ネ", "ne"), ("ノ", "no")],
    [("ハ", "ha"), ("ヒ", "hi"), ("フ", "fu"), ("ヘ", "he"), ("ホ", "ho")],
    [("マ", "ma"), ("ミ", "mi"), ("ム", "mu"), ("メ", "me"), ("モ", "mo")],
    [("ヤ", "ya"), ("ユ", "yu"), ("ヨ", "yo")],
    [("ラ", "ra"), ("リ", "ri"), ("ル", "ru"), ("レ", "re"), ("ロ", "ro")],
    [("ワ", "wa"), ("ヲ", "wo"), ("ン", "n")],
]

# Focused radical/component hints for high-frequency and commonly confused kanji.
RADICAL_HINTS = {
    "日": "Radical: 日 (sun/day). This shape often appears in time and calendar words.",
    "目": "Radical: 目 (eye). Think of an eye shape; many body/seeing words use it.",
    "月": "Radical: 月 (moon/flesh). In time words it usually means month/moon.",
    "木": "Radical: 木 (tree). Related forms often involve plants or wood.",
    "林": "Component idea: 木 + 木 (two trees) -> woods.",
    "森": "Component idea: 木 + 木 + 木 (many trees) -> forest.",
    "休": "Component idea: 亻(person) + 木(tree) -> person resting by a tree.",
    "体": "Component idea: 亻(person) + 本(base/origin) -> body as the person's base.",
    "明": "Component idea: 日(sun) + 月(moon) -> bright/clear.",
    "男": "Component idea: 田(field) + 力(power) -> traditional image of field labor.",
    "好": "Component idea: 女(woman) + 子(child) -> like/fond of.",
    "語": "Radical: 言 (speech). Words with this radical often relate to language/speaking.",
    "読": "Radical: 言 (speech) + 売 component. Reading is language processing.",
    "話": "Radical: 言 (speech). Keep this in the speaking/communication family.",
    "聞": "Component idea: 門(gate) + 耳(ear) -> hear through a gate.",
    "間": "Component idea: 門(gate) + 日(sun) -> space/time between.",
    "電": "Radical: 雨 (rain) on top. Many weather/electricity kanji use this pattern.",
    "駅": "Radical: 馬 (horse) historically linked to transport stations.",
    "海": "Radical: 氵(water). Water radical often marks liquids/sea/river meanings.",
    "河": "Radical: 氵(water). Helps classify it as a water-related kanji.",
    "湖": "Radical: 氵(water). Lake-related meaning is signaled by the water side.",
    "情": "Radical: 忄(heart). Emotion/feeling kanji often use this radical.",
    "忙": "Radical: 忄(heart). Emotional/mental state family.",
    "想": "Radical idea: 心(heart) at bottom supports thought/feeling meaning.",
    "持": "Radical: 扌(hand). Hand radical often marks physical actions.",
    "打": "Radical: 扌(hand). Action with the hand.",
    "投": "Radical: 扌(hand). Throwing/action family.",
    "飲": "Radical: 飠(food). Food/eating/drinking vocabulary family.",
    "食": "Radical: 食(food). Core food-related character.",
    "飯": "Radical: 飠(food). Meal/rice meaning in food family.",
    "校": "Radical: 木 (tree/wood). In compounds, often tied to school/structure words.",
    "学": "Component idea: top cover + child 子; linked to study/learning.",
    "先": "Component idea: person/legs shape; often appears in sequence/priority words.",
    "生": "Core life/grow character. Often seen in words for life, birth, student.",
    "時": "Component idea: 日(day/time) + 寺. Strongly tied to time expressions.",
    "分": "Component idea: divide/split. Used in minutes and part/portion words.",
    "半": "Half marker kanji. Useful for time expressions like half past.",
    "今": "Current/present marker. Common in time words like today/now.",
    "何": "Question kanji used in what/how many compounds.",
    "外": "Outside marker. Often contrasts with 内 (inside).",
    "内": "Inside marker. Pair with 外 for location opposites.",
    "前": "Before/front marker in time and position contexts.",
    "後": "After/back marker in time and position contexts.",
    "左": "Left direction kanji; often learned with 右.",
    "右": "Right direction kanji; often learned with 左.",
    "東": "East direction kanji; often learned with 西/南/北.",
    "西": "West direction kanji; often learned with 東/南/北.",
    "南": "South direction kanji; geography set member.",
    "北": "North direction kanji; geography set member.",
    "雨": "Radical: 雨 (rain/weather). Often marks weather-related kanji.",
    "雪": "Radical: 雨 (rain/weather). Snow/weather family.",
    "雲": "Radical: 雨 (rain/weather). Cloud/weather family.",
    "天": "Sky/heaven marker used in weather and abstract compounds.",
    "気": "Air/spirit marker used in many abstract words.",
    "空": "Sky/empty kanji. Often appears in weather and space words.",
    "場": "Radical: 土 (earth/place). Often indicates a place/location.",
    "地": "Radical: 土 (earth). Ground/land/location family.",
    "図": "Diagram/map family; appears in planning/visual words.",
    "館": "Radical: 飠 historically; now often means building/hall in compounds.",
    "門": "Gate radical. Related to openings/entry concepts.",
    "開": "Gate-based kanji for open/start.",
    "閉": "Gate-based kanji for close/shut.",
    "店": "Shop/store marker in commerce vocabulary.",
    "買": "Buy action marker in shopping vocabulary.",
    "売": "Sell action marker in shopping vocabulary.",
    "物": "Thing/object marker in many noun compounds.",
    "者": "Person suffix marker (one who does X).",
    "会": "Meet/association marker in social and business words.",
    "社": "Company/shrine marker; business vocabulary family.",
    "員": "Member/staff suffix in role words.",
    "仕": "Serve/work component in job-related words.",
    "事": "Matter/event marker in abstract and work words.",
    "働": "Person radical + movement; work/labor meaning.",
    "業": "Business/industry marker in advanced vocabulary.",
    "職": "Ear + halberd structure; occupation/profession family.",
    "医": "Medicine/healing family marker.",
    "病": "Sickness radical 疒; health/illness vocabulary.",
    "院": "Institution marker in hospital/school compounds.",
    "薬": "Medicine marker with plant radical.",
    "旅": "Travel/journey marker.",
    "運": "Movement/transport marker with road radical 辶.",
    "転": "Turn/roll marker in transport words.",
    "路": "Road/path marker in route vocabulary.",
    "速": "Fast/speed marker.",
    "遅": "Slow/late marker; often paired with 速.",
    "進": "Advance/progress marker with movement radical.",
    "退": "Retreat/withdraw marker with movement radical.",
    "発": "Departure/start marker in schedule vocabulary.",
    "着": "Arrive/wear marker in movement and clothing words.",
    "配": "Distribution/delivery marker with alcohol pot radical 酉.",
    "送": "Send/transport marker with movement radical.",
    "親": "Parent/intimate marker in family words.",
    "兄": "Older brother marker in family set.",
    "姉": "Older sister marker with woman radical.",
    "弟": "Younger brother marker in family set.",
    "妹": "Younger sister marker with woman radical.",
    "妻": "Wife marker in family vocabulary.",
    "夫": "Husband marker in family vocabulary.",
    "味": "Taste/flavor marker with mouth radical 口.",
    "料": "Material/fee marker in food and cost words.",
    "理": "Logic/reason marker in abstract compounds.",
    "主": "Main/master marker in role and grammar words.",
    "注": "Water radical + main; often relates to pouring/attention.",
    "住": "Person radical + main; often tied to residence.",
    "返": "Return marker with movement radical.",
    "決": "Water radical + decisive component; decide/fix meaning.",
    "定": "Fixed/decide marker in planning vocabulary.",
    "表": "Surface/express marker.",
    "現": "King/jewel radical + see component; appear/actual.",
    "実": "Real/actual marker in abstract set.",
    "真": "True marker in abstract and adjective compounds.",
    "動": "Move marker in action-related words.",
    "静": "Quiet/still marker; opposite of active/moving terms.",
    "重": "Heavy/important marker in many compounds.",
    "軽": "Light marker, often contrasted with 重.",
    "強": "Strong marker in ability/strength words.",
    "弱": "Weak marker in ability/strength words.",
    "新": "New marker in time/product descriptors.",
    "古": "Old marker; often paired with 新.",
    "高": "Tall/expensive marker in adjective set.",
    "安": "Cheap/safe marker in adjective set.",
    "低": "Low marker in position/value words.",
    "広": "Wide marker in space descriptors.",
    "細": "Thin/fine marker with thread radical 糸.",
    "太": "Thick/fat marker; easy to confuse with 犬 visually.",
    "漢": "Water radical + complex right side; Sino/Japanese language context.",
    "字": "Character/letter marker.",
    "文": "Sentence/writing marker in language set.",
    "話": "Speech radical 言 family; conversation words.",
    "語": "Speech radical 言 family; language words.",
    "読": "Speech radical 言 family; reading words.",
    "書": "Write/document marker in literacy set.",
    "試": "Speech radical + test component; examination words.",
    "験": "Horse radical 馬 family; exam/verification words.",
    "習": "Feather-based component; practice/learning words.",
    "教": "Teach/instruction marker.",
    "答": "Answer marker in question-answer vocabulary.",
    "問": "Gate + mouth; ask/question marker.",
    "題": "Topic/problem marker in study and test contexts.",
    "由": "Reason/origin marker in abstract words.",
    "経": "Thread radical 糸; pass through/experience.",
    "済": "Water radical variant; finish/settle/economy meanings.",
    "難": "Bird + complex form; difficult marker.",
    "簡": "Bamboo radical ⺮; simple marker often paired with 難.",
}

# Confusable groups; only shown when both items exist in the same JLPT level dataset.
CONFUSABLE_GROUPS = [
    ("日", "目", "Both are box-like; 日 is day/sun, 目 is eye."),
    ("人", "入", "人 is person; 入 is enter. Stroke angle and opening differ."),
    ("土", "士", "Top/bottom stroke lengths are swapped."),
    ("未", "末", "Bottom vs top longer stroke; meanings differ (not yet vs end)."),
    ("犬", "太", "Tiny dot position changes meaning completely."),
    ("木", "本", "本 adds a bottom marker line for 'base/origin'."),
    ("木", "休", "休 includes person radical 亻 on the left."),
    ("口", "日", "口 is mouth; 日 has inner horizontal and day meaning."),
    ("千", "干", "Short extra stroke/shape difference; do not merge them."),
    ("言", "計", "計 contains 言 plus extra component; watch right side details."),
    ("末", "朱", "Both have crossing strokes; meaning set differs (end vs vermilion)."),
    ("牛", "午", "Small stroke position difference; meanings unrelated."),
    ("己", "已", "Very similar cursive-like shapes; memorize final stroke position."),
    ("口", "回", "回 encloses another box, unlike single-box 口."),
    ("土", "工", "Similar horizontals; center stroke behavior differs."),
    ("白", "百", "百 adds top line and number meaning."),
    ("王", "玉", "玉 has an extra dot stroke; king vs jewel."),
    ("手", "毛", "Shape overlap; watch top stroke and hook behavior."),
    ("待", "持", "Left radical differs: 彳 for movement vs 扌 for hand action."),
    ("聞", "問", "Both use 門; inside component differs (耳 vs 口)."),
    ("晴", "清", "Left radical differs: 日 (weather/day) vs 氵 (water/clear)."),
    ("情", "晴", "Shared 青-like right side; left radical drives meaning (heart vs sun)."),
    ("続", "読", "Complex right side and radicals differ; thread vs speech family."),
    ("検", "険", "Very close forms; left radicals differ (wood vs hill)."),
    ("議", "儀", "Shared right structure; speech radical 言 vs person radical 亻."),
    ("講", "構", "Similar right component; speech radical 言 vs wood radical 木."),
    ("導", "道", "導 includes hand/寸 element; meaning extends from path to guidance."),
    ("際", "障", "Both often in abstract contexts; left-side hill radical plus different right parts."),
    ("製", "制", "Shared control-related shape; clothing radical at top changes word family."),
    ("適", "滴", "Movement radical 辶 vs water radical 氵; pronunciation often similar."),
    ("環", "還", "Jewel radical 王 variant vs movement radical 辶; close right-side shape."),
    ("証", "症", "Speech radical 言 vs sickness radical 疒; same sound in many compounds."),
    ("資", "姿", "Shell/money radical 貝 vs woman radical 女 on lower half."),
    ("編", "偏", "Thread radical 糸 vs person radical 亻 with similar right side.")
]


def to_hiragana(text):
    if not text:
        return ""
    if kakasi is None:
        return ""
    kks = kakasi()
    converted = kks.convert(text)
    return clean_text("".join(part.get("hira", "") for part in converted))


def to_romaji(text):
    if not text:
        return ""
    if kakasi is None:
        return ""
    kks = kakasi()
    converted = kks.convert(text)
    return clean_text(" ".join(part.get("hepburn", "") for part in converted))


def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "denkodojo-data-builder/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def clean_text(value):
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def contains_kanji(text):
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def pick_primary_meaning(meanings, level_key=None, character=None):
    cleaned = [clean_text(m) for m in (meanings or []) if clean_text(m)]
    if not cleaned:
        return ""

    if level_key == "n5" and character in PRIMARY_MEANING_OVERRIDES_N5:
        return PRIMARY_MEANING_OVERRIDES_N5[character]

    # Split composite meanings and score for learner-friendly sense.
    candidates = []
    for item in cleaned:
        for part in [clean_text(x) for x in re.split(r";|,", item) if clean_text(x)]:
            candidates.append(part)

    if not candidates:
        return cleaned[0]

    def score(candidate):
        c = candidate.lower()
        s = 100
        if any(h in c for h in MEANING_BAD_HINTS):
            s -= 50
        # Prefer short, clear glosses like "school", "book", "go".
        words = len(c.split())
        s -= min(words, 6) * 3
        if "(" in c or ")" in c:
            s -= 10
        return s

    ranked = sorted(candidates, key=score, reverse=True)
    return ranked[0]


def is_safe_example(sentence_jp, sentence_en):
    jp = clean_text(sentence_jp)
    en = clean_text(sentence_en)
    if not jp and not en:
        return False
    for pat in UNSAFE_EN_PATTERNS:
        if pat.search(en):
            return False
    for pat in UNSAFE_JP_PATTERNS:
        if pat.search(jp):
            return False
    return True


def select_safe_example(examples, word, meanings):
    for ex in examples or []:
        jp = clean_text(ex.get("ja"))
        en = clean_text(ex.get("en"))
        if is_safe_example(jp, en):
            return jp, en

    # Neutral fallback if no safe example is available.
    fallback_en = pick_primary_meaning(meanings) if meanings else ""
    return f"{word}です。", fallback_en


def parse_example_with_span(example_text):
    if not example_text:
        return "", ""

    match = re.search(r"(.*?)<span>(.*?)</span>", example_text)
    if match:
        jp = clean_text(html.unescape(match.group(1)))
        en = clean_text(html.unescape(match.group(2)))
        return jp, en

    # Fallback if source format changes.
    plain = clean_text(re.sub(r"<[^>]+>", "", example_text))
    return plain, ""


def is_kana_only(text):
    if not text:
        return False
    return bool(re.fullmatch(r"[\u3040-\u30ffー・\s]+", text))


def build_kanji_note(level_key, meanings, onyomi, kunyomi, example_word):
    first_meaning = clean_text(meanings[0]) if meanings else "basic concept"
    on_count = len(onyomi)
    kun_count = len(kunyomi)
    reading_tip = f"On-reading count: {on_count}; Kun-reading count: {kun_count}."
    example_tip = ""
    if example_word.get("jp") and example_word.get("reading"):
        example_tip = (
            f"Learn it in context with {example_word['jp']} ({example_word['reading']}) first, "
            "then recall the character meaning."
        )
    return (
        f"JLPT {level_key.upper()} focus: {first_meaning}. {reading_tip} "
        f"{example_tip}"
    ).strip()


def build_kanji_study_note(level_key, item, level_chars, example_word, primary_meaning):
    character = clean_text(item.get("character"))
    first_meaning = clean_text(primary_meaning) if primary_meaning else "core meaning"
    strokes = item.get("strokes") or 0

    radical_hint = RADICAL_HINTS.get(character)
    if not radical_hint:
        radical_hint = "Radical/component hint: break this kanji into left-right or top-bottom chunks before memorizing."

    similar_bits = []
    for a, b, note in CONFUSABLE_GROUPS:
        if character == a and b in level_chars:
            similar_bits.append(f"Similar in {level_key.upper()}: {b}. {note}")
        elif character == b and a in level_chars:
            similar_bits.append(f"Similar in {level_key.upper()}: {a}. {note}")

    if similar_bits:
        similar_tip = similar_bits[0]
    else:
        similar_tip = f"Compare this with other {level_key.upper()} kanji that share strokes to avoid shape-mix errors."

    if strokes >= 12:
        memory_tip = (
            f"Memory tip for complex kanji ({strokes} strokes): memorize in 2 chunks, "
            "trace each chunk 5 times, then write the full character 3 times from memory."
        )
    else:
        memory_tip = "Memory tip: say meaning + reading aloud while writing once, then recall it in the example word."

    example_tip = ""
    if example_word.get("jp") and example_word.get("reading"):
        example_tip = f"Usage anchor: {example_word['jp']} ({example_word['reading']})."

    return (
        f"Focus meaning: {first_meaning}. "
        f"{radical_hint} "
        f"{similar_tip} "
        f"{memory_tip} "
        f"{example_tip}"
    ).strip()


def build_vocab_note(level_key, word, reading, meanings, sentence_jp):
    first_meaning = clean_text(meanings[0]) if meanings else ""
    tips = [f"JLPT {level_key.upper()} word for '{first_meaning}'." if first_meaning else f"JLPT {level_key.upper()} vocabulary item."]
    if reading and reading != word:
        tips.append(f"Read it as {reading}.")
    elif is_kana_only(word):
        tips.append("Kana-only word: prioritize listening and sentence context over kanji breakdown.")
    else:
        tips.append("Kanji form carries meaning clues, so review the character meanings while memorizing this word.")
    if sentence_jp:
        tips.append("Shadow the example sentence aloud 3 times to lock in natural usage.")
    return " ".join(tips)


def build_grammar_note(level_key, section_title, pattern, meaning):
    notes = [f"JLPT {level_key.upper()} grammar in {section_title}."]
    if pattern:
        notes.append(f"Pattern: {pattern}.")
    if meaning:
        notes.append(f"Core meaning: {meaning}.")
    notes.append("Practice by writing one personal sentence and one question using this structure.")
    return " ".join(notes)


def build_kanji_entries(level_key, kanji_raw, vocab_raw):
    # Build lightweight char->example lookup for nicer kanji cards.
    char_to_vocab = {}
    for item in vocab_raw:
        word = clean_text(item.get("word"))
        if not word:
            continue
        for ch in word:
            if ch not in char_to_vocab and any("\u4e00" <= c <= "\u9fff" for c in ch):
                first_meaning = ""
                meanings = item.get("meanings") or []
                if meanings:
                    first_meaning = pick_primary_meaning(meanings)
                char_to_vocab[ch] = {
                    "jp": word,
                    "reading": clean_text(item.get("reading")) or word,
                    "en": first_meaning,
                }

    out = []
    level_chars = {clean_text(item.get("character")) for item in kanji_raw if clean_text(item.get("character"))}
    for item in kanji_raw:
        character = clean_text(item.get("character"))
        if not character:
            continue

        onyomi = item.get("onyomi") or []
        kunyomi = item.get("kunyomi") or []
        meanings = item.get("meanings") or []
        primary_meaning = pick_primary_meaning(meanings, level_key=level_key, character=character)

        example_word = char_to_vocab.get(character) or {
            "jp": character,
            "reading": clean_text(kunyomi[0] if kunyomi else (onyomi[0] if onyomi else character)),
            "en": primary_meaning,
        }

        out.append(
            {
                "char": character,
                "on": clean_text(" / ".join(onyomi) if onyomi else "-"),
                "kun": clean_text(" / ".join(kunyomi) if kunyomi else "-"),
                "meaning": primary_meaning,
                "word": {
                    "jp": clean_text(example_word.get("jp")),
                    "reading": clean_text(example_word.get("reading")),
                    "en": clean_text(example_word.get("en")),
                },
                "note": build_kanji_study_note(level_key, item, level_chars, example_word, primary_meaning),
            }
        )

    return out


def build_vocab_entries(level_key, vocab_raw):
    out = []
    for item in vocab_raw:
        word = clean_text(item.get("word"))
        if not word:
            continue

        meanings = [clean_text(m) for m in (item.get("meanings") or []) if clean_text(m)]
        examples = item.get("examples") or []

        sentence_jp, sentence_en = select_safe_example(examples, word, meanings)

        # Auto-kana/romaji can be wrong for mixed-kanji sentences; leave empty unless fully kana.
        if contains_kanji(sentence_jp):
            sentence_furigana = ""
            sentence_romaji = ""
        else:
            sentence_furigana = to_hiragana(sentence_jp)
            sentence_romaji = ""

        out.append(
            {
                "jp": word,
                "reading": clean_text(item.get("reading")) or word,
                "meaning": pick_primary_meaning(meanings),
                "sentence": {
                    "jp": sentence_jp,
                    "furigana": sentence_furigana,
                    "romaji": sentence_romaji,
                    "en": sentence_en,
                },
                "note": build_vocab_note(level_key, word, clean_text(item.get("reading")) or word, meanings, sentence_jp),
            }
        )

    return out


def build_grammar_entries(level_key, grammar_raw):
    level_blob = grammar_raw.get(level_key, {})
    sections = level_blob.get("sections") or []
    out = []

    for section in sections:
        section_title = clean_text(section.get("title"))
        cards = section.get("cards") or []

        for card in cards:
            pattern = clean_text(card.get("jp")) or clean_text(card.get("point"))
            meaning = clean_text(card.get("meaning"))
            structure = clean_text(card.get("point")) or pattern
            example = clean_text(card.get("example"))
            sentence_jp, sentence_en = parse_example_with_span(example)

            if not sentence_jp:
                sentence_jp = pattern

            if contains_kanji(sentence_jp):
                sentence_furigana = ""
                sentence_romaji = ""
            else:
                sentence_furigana = to_hiragana(sentence_jp)
                sentence_romaji = ""

            out.append(
                {
                    "pattern": pattern,
                    "meaning": meaning,
                    "structure": structure,
                    "sentence": {
                        "jp": sentence_jp,
                        "furigana": sentence_furigana,
                        "romaji": sentence_romaji,
                        "en": sentence_en,
                    },
                    "note": build_grammar_note(level_key, section_title, pattern, meaning),
                }
            )

    return out


def flatten_kana_rows(rows, script_name):
    out = []
    for row in rows:
        row_romaji = ", ".join(item[1] for item in row)
        for char, reading in row:
            out.append(
                {
                    "char": char,
                    "reading": reading,
                    "meaning": f"{script_name} syllable '{reading}'",
                    "row": row_romaji,
                    "example": {
                        "jp": char,
                        "romaji": reading,
                        "en": f"Sound: {reading}",
                    },
                    "note": (
                        f"Practice tip: say '{reading}' aloud, trace {char} 5 times, "
                        "then write it once from memory."
                    ),
                }
            )
    return out


def build_beginner_practice():
    return [
        {
            "pattern": "Vowel set drill",
            "meaning": "Read all five vowels smoothly",
            "structure": "a i u e o",
            "sentence": {
                "jp": "あ い う え お / ア イ ウ エ オ",
                "furigana": "あ い う え お / あ い う え お",
                "romaji": "a i u e o",
                "en": "Say both scripts without pausing.",
            },
            "note": "Keep a steady rhythm. Aim for speed only after accuracy is stable.",
        },
        {
            "pattern": "K-row drill",
            "meaning": "Build consonant + vowel awareness",
            "structure": "ka ki ku ke ko",
            "sentence": {
                "jp": "か き く け こ / カ キ ク ケ コ",
                "furigana": "か き く け こ / か き く け こ",
                "romaji": "ka ki ku ke ko",
                "en": "Read both scripts and compare shapes.",
            },
            "note": "Pair each hiragana with matching katakana to reduce confusion.",
        },
        {
            "pattern": "S-row drill",
            "meaning": "Pay attention to shi",
            "structure": "sa shi su se so",
            "sentence": {
                "jp": "さ し す せ そ / サ シ ス セ ソ",
                "furigana": "さ し す せ そ / さ し す せ そ",
                "romaji": "sa shi su se so",
                "en": "Focus on the irregular reading 'shi'.",
            },
            "note": "Mark shi as a special sound; review it daily until automatic.",
        },
        {
            "pattern": "T-row drill",
            "meaning": "Differentiate chi and tsu",
            "structure": "ta chi tsu te to",
            "sentence": {
                "jp": "た ち つ て と / タ チ ツ テ ト",
                "furigana": "た ち つ て と / た ち つ て と",
                "romaji": "ta chi tsu te to",
                "en": "Focus on irregular readings chi and tsu.",
            },
            "note": "Use slow repetition: chi-tsu-chi-tsu before full-row reading.",
        },
        {
            "pattern": "N-row + final n",
            "meaning": "Build nasal sound control",
            "structure": "na ni nu ne no + n",
            "sentence": {
                "jp": "な に ぬ ね の + ん / ナ ニ ヌ ネ ノ + ン",
                "furigana": "な に ぬ ね の + ん / な に ぬ ね の + ん",
                "romaji": "na ni nu ne no + n",
                "en": "Practice ending clearly with ん (n).",
            },
            "note": "Pause slightly before ん to avoid blending into the next sound.",
        },
    ]


def build_beginner_useful_words():
    # Kana-first practical words for absolute beginners.
    raw = [
        ("Greetings", "おはよう", "ohayou", "good morning", "おはよう！", "ohayou", "Good morning!", "Friendly morning greeting."),
        ("Greetings", "こんにちは", "konnichiwa", "hello", "こんにちは。", "konnichiwa", "Hello.", "Standard daytime greeting."),
        ("Greetings", "こんばんは", "konbanwa", "good evening", "こんばんは。", "konbanwa", "Good evening.", "Use this after sunset."),
        ("Greetings", "おやすみ", "oyasumi", "good night", "おやすみ。", "oyasumi", "Good night.", "Casual bedtime phrase."),
        ("Greetings", "ありがとう", "arigatou", "thank you", "ありがとう！", "arigatou", "Thank you!", "Casual thank you phrase."),
        ("Greetings", "ありがとうございます", "arigatou gozaimasu", "thank you (polite)", "ありがとうございます。", "arigatou gozaimasu", "Thank you very much.", "Polite version for formal situations."),
        ("Essentials", "すみません", "sumimasen", "excuse me / sorry", "すみません、トイレはどこですか。", "sumimasen, toire wa doko desu ka", "Excuse me, where is the toilet?", "Useful for apology or getting attention."),
        ("Essentials", "ごめんなさい", "gomennasai", "I am sorry", "ごめんなさい。", "gomennasai", "I am sorry.", "Direct apology phrase."),
        ("Essentials", "はい", "hai", "yes", "はい、わかりました。", "hai, wakarimashita", "Yes, I understand.", "Polite affirmation."),
        ("Essentials", "いいえ", "iie", "no", "いいえ、だいじょうぶです。", "iie, daijoubu desu", "No, I am okay.", "Polite negative response."),
        ("Essentials", "おねがいします", "onegaishimasu", "please", "みずをおねがいします。", "mizu o onegaishimasu", "Water, please.", "Very common polite request phrase."),
        ("Essentials", "だいじょうぶ", "daijoubu", "okay / all right", "だいじょうぶです。", "daijoubu desu", "It is okay.", "Use for both safety and confirmation."),
        ("Essentials", "わかりました", "wakarimashita", "understood", "はい、わかりました。", "hai, wakarimashita", "Yes, understood.", "Polite acknowledgement phrase."),
        ("Essentials", "わかりません", "wakarimasen", "I do not understand", "すみません、わかりません。", "sumimasen, wakarimasen", "Sorry, I do not understand.", "Useful when you need repetition/help."),
        ("Navigation", "これ", "kore", "this", "これはなんですか。", "kore wa nan desu ka", "What is this?", "Points to something near you."),
        ("Navigation", "それ", "sore", "that", "それはおいしいです。", "sore wa oishii desu", "That is delicious.", "Points to something near the listener."),
        ("Navigation", "あれ", "are", "that over there", "あれはえきです。", "are wa eki desu", "That over there is the station.", "Points to something far from both people."),
        ("Navigation", "ここ", "koko", "here", "ここでまってください。", "koko de matte kudasai", "Please wait here.", "Location near speaker."),
        ("Navigation", "そこ", "soko", "there", "そこにあります。", "soko ni arimasu", "It is there.", "Location near listener."),
        ("Navigation", "どこ", "doko", "where", "トイレはどこですか。", "toire wa doko desu ka", "Where is the toilet?", "Essential navigation word."),
        ("Navigation", "トイレ", "toire", "toilet", "トイレはどこですか。", "toire wa doko desu ka", "Where is the toilet?", "Essential travel word."),
        ("Shopping and Food", "みず", "mizu", "water", "みずをください。", "mizu o kudasai", "Water, please.", "Simple food/drink request word."),
        ("Shopping and Food", "ごはん", "gohan", "meal / rice", "ごはんをたべます。", "gohan o tabemasu", "I eat a meal.", "Daily food vocabulary."),
        ("Shopping and Food", "いくら", "ikura", "how much", "これはいくらですか。", "kore wa ikura desu ka", "How much is this?", "Useful for shopping."),
        ("Shopping and Food", "ください", "kudasai", "please give me", "これをください。", "kore o kudasai", "Please give me this.", "Core shopping/request phrase."),
        ("Shopping and Food", "おいしい", "oishii", "delicious", "おいしいです！", "oishii desu", "It is delicious!", "Useful compliment at meals."),
        ("Time", "いま", "ima", "now", "いまいきます。", "ima ikimasu", "I am going now.", "Basic time word."),
        ("Time", "きょう", "kyou", "today", "きょうはあついです。", "kyou wa atsui desu", "Today is hot.", "Daily time expression."),
        ("Time", "あした", "ashita", "tomorrow", "あしたいきます。", "ashita ikimasu", "I will go tomorrow.", "Very common beginner time word."),
        ("Time", "なんじ", "nanji", "what time", "いまなんじですか。", "ima nanji desu ka", "What time is it now?", "Core question for schedules."),
        ("Navigation", "えき", "eki", "station", "えきはどこですか。", "eki wa doko desu ka", "Where is the station?", "Essential navigation word."),
    ]

    out = []
    for group, jp, reading, meaning, ex_jp, ex_romaji, ex_en, note in raw:
        out.append(
            {
                "group": group,
                "jp": jp,
                "reading": reading,
                "meaning": meaning,
                "sentence": {
                    "jp": ex_jp,
                    "furigana": to_hiragana(ex_jp),
                    "romaji": ex_romaji,
                    "en": ex_en,
                },
                "note": note,
            }
        )
    return out


def build_beginner_data():
    return {
        "hiragana": flatten_kana_rows(HIRAGANA_ROWS, "Hiragana"),
        "katakana": flatten_kana_rows(KATAKANA_ROWS, "Katakana"),
        "useful_words": build_beginner_useful_words(),
        "practice": build_beginner_practice(),
    }


def build_database():
    print("Building complete N5-N1 data (kanji, vocab, grammar)...")

    grammar_raw = fetch_json(GRAMMAR_URL)

    data = {lvl: {"kanji": [], "vocab": [], "grammar": []} for lvl in JLPT_LEVELS}
    data["beginner"] = build_beginner_data()

    for lvl in JLPT_LEVELS:
        print(f"Fetching {lvl.upper()} kanji...")
        kanji_raw = fetch_json(f"{KANJI_BASE}/{lvl}.json")

        print(f"Fetching {lvl.upper()} vocab...")
        vocab_raw = fetch_json(f"{VOCAB_BASE}/{lvl}.json")

        print(f"Transforming {lvl.upper()} payloads...")
        data[lvl]["kanji"] = build_kanji_entries(lvl, kanji_raw, vocab_raw)
        data[lvl]["vocab"] = build_vocab_entries(lvl, vocab_raw)
        data[lvl]["grammar"] = build_grammar_entries(lvl, grammar_raw)

    js_output = f"/* Auto-generated by build_data.py */\nconst DATA = {json.dumps(data, ensure_ascii=False, indent=2)};\n"

    output_path = os.path.join(os.path.dirname(__file__), "data.js")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(js_output)

    print("Done. data.js updated.")
    print(
        "BEGINNER: "
        f"hiragana={len(data['beginner']['hiragana'])}, "
        f"katakana={len(data['beginner']['katakana'])}, "
        f"useful_words={len(data['beginner']['useful_words'])}, "
        f"practice={len(data['beginner']['practice'])}"
    )
    for lvl in JLPT_LEVELS:
        print(
            f"{lvl.upper()}: "
            f"kanji={len(data[lvl]['kanji'])}, "
            f"vocab={len(data[lvl]['vocab'])}, "
            f"grammar={len(data[lvl]['grammar'])}"
        )


if __name__ == "__main__":
    build_database()
