import os
import json
import random

# Create directory if it doesn't exist
os.makedirs("subjects/english/curriculum", exist_ok=True)

short_vowel_a_skills = {
    "english_3_s27": {
        "title_ar": "الحركات القصيرة: Short a (an_01)",
        "title_en": "Short Vowel a (an_01)",
        "instructions_ar": "هيا نتعلم الحركات القصيرة مع الكلمات التي تنتهي بـ an! 🌟",
        "instructions_en": "Let's learn short vowel a words ending with an! 🌟",
        "words": ["Pan", "Fan", "Can", "Tan"]
    },
    "english_3_s28": {
        "title_ar": "الحركات القصيرة: Short a (an_02)",
        "title_en": "Short Vowel a (an_02)",
        "instructions_ar": "هيا نتعلم المزيد من كلمات الحركة القصيرة an! 🌟",
        "instructions_en": "Let's learn more short vowel a words ending with an! 🌟",
        "words": ["Man", "Ran", "Van"]
    },
    "english_3_s29": {
        "title_ar": "الحركات القصيرة: Short a (ap_01)",
        "title_en": "Short Vowel a (ap_01)",
        "instructions_ar": "هيا نتعلم الحركات القصيرة مع الكلمات التي تنتهي بـ ap! 🌟",
        "instructions_en": "Let's learn short vowel a words ending with ap! 🌟",
        "words": ["Cap", "Tap", "Map", "Nap"]
    },
    "english_3_s30": {
        "title_ar": "الحركات القصيرة: Short a (ad)",
        "title_en": "Short Vowel a (ad)",
        "instructions_ar": "هيا نتعلم الحركات القصيرة مع الكلمات التي تنتهي بـ ad! 🌟",
        "instructions_en": "Let's learn short vowel a words ending with ad! 🌟",
        "words": ["Dad", "Mad", "Bad", "Sad"]
    }
}

# Distractor consonant pool for spelling options
consonants_pool = ['b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z']

# Gather all vocabulary words across alphabet and short vowels to use as distractors in audio questions
alphabet_vocab_words = [
    "Apple", "Ant", "Axe", "Ball", "Bee", "Book", "Car", "Cat", "Cow", "Duck", "Dog", "Drum",
    "Elephant", "Egg", "Ear", "Flag", "Fish", "Fox", "Gift", "Goat", "Glass", "Hand", "Hen", "Hair",
    "Ice cream", "Iron", "Insect", "Jam", "Jacket", "Juice", "Key", "King", "Kite", "Lemon", "Lion", "Leg",
    "Moon", "Monkey", "Man", "Nose", "Nurse", "Nest", "Orange", "Oil", "Olives", "Plane", "Pen", "Pencil",
    "Queen", "Quarter", "Quiet", "Ruler", "Rabbit", "Ring", "Sun", "Snake", "Star", "Tree", "Table", "Train",
    "Umbrella", "Up", "Uncle", "Vegetable", "Violin", "Vase", "Watermelon", "Window", "Watch", "X-ray", "Xylophone", "Box",
    "Yellow", "Yoyo", "Yacht", "Zoo", "Zebra", "Zipper", "Pan", "Fan", "Can", "Tan", "Ran", "Van", "Cap", "Tap", "Map", "Nap",
    "Dad", "Mad", "Bad", "Sad"
]

def get_image_path(w):
    base_name = w.lower().replace(' ', '_')
    png_path = f"assets/images/{base_name}.png"
    if os.path.exists(png_path):
        return png_path
    return f"assets/images/{base_name}.svg"

level_data = {}

for skill_id, info in short_vowel_a_skills.items():
    words = info["words"]
    questions = []

    # 1. Supply the missing character (missing-letter) for each word
    for w in words:
        correct_letter = w[0].lower()
        display_word = "_" + w[1:].lower() # e.g. "_an"
        image_path = get_image_path(w)

        # Build 8 choices (1 correct + 7 unique distractors)
        choices = [correct_letter]
        other_consonants = [c for c in consonants_pool if c != correct_letter]
        choices.extend(random.sample(other_consonants, 7))
        random.shuffle(choices)

        questions.append({
            "type": "missing-letter",
            "question": "Choose the missing starting letter! ✍️",
            "word": w,
            "missing_letter": correct_letter,
            "display_word": display_word,
            "image": image_path,
            "options": choices,
            "correct": correct_letter
        })

    # 2. Listen and choose the word (audio-choice with standard image options) for each word
    for w in words:
        correct_img_path = get_image_path(w)
        
        # Select 3 distractor words from all words
        distractor_pool = [item for item in alphabet_vocab_words if item != w]
        distractors = random.sample(distractor_pool, 3)

        options = [
            {"text": w, "image": correct_img_path},
            {"text": distractors[0], "image": get_image_path(distractors[0])},
            {"text": distractors[1], "image": get_image_path(distractors[1])},
            {"text": distractors[2], "image": get_image_path(distractors[2])}
        ]
        random.shuffle(options)

        questions.append({
            "type": "audio-choice",
            "question": "Listen to the word and choose the matching picture! 🔊",
            "speak_text": w,
            "options": options,
            "correct": w
        })

    # 3. Match image beside word (drag-and-drop)
    # Match all words in this skill group
    items = []
    targets = []
    for w in words:
        w_san = w.lower().replace(' ', '_')
        items.append({
            "id": f"drag-{w_san}",
            "image": get_image_path(w)
        })
        targets.append({
            "id": f"drop-{w_san}",
            "text": w,
            "matches": f"drag-{w_san}"
        })
    
    random.shuffle(items) # Shuffle drag items

    questions.append({
        "type": "drag-and-drop",
        "question": "Drag each picture to its matching word basket!",
        "items": items,
        "targets": targets
    })

    level_data[skill_id] = {
        "id": skill_id,
        "age_group": 3,
        "subject": "english",
        "title_ar": info["title_ar"],
        "title_en": info["title_en"],
        "instructions_ar": info["instructions_ar"],
        "instructions_en": info["instructions_en"],
        "questions": questions
    }

# Save output
output_filepath = "subjects/english/curriculum/short_vowel_a.json"
with open(output_filepath, "w", encoding="utf-8") as f:
    json.dump(level_data, f, indent=2, ensure_ascii=False)

print(f"Successfully generated short vowel A curriculum file at: {output_filepath}")
