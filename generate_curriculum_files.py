import os
import json
import random

# Create directory if it doesn't exist
os.makedirs("subjects/english/curriculum", exist_ok=True)

# List of letters and their 3 vocabulary words
alphabet_vocab = [
    ("A", ["Apple", "Ant", "Axe"]),
    ("B", ["Ball", "Bee", "Book"]),
    ("C", ["Car", "Cat", "Cow"]),
    ("D", ["Duck", "Dog", "Drum"]),
    ("E", ["Elephant", "Egg", "Ear"]),
    ("F", ["Flag", "Fish", "Fox"]),
    ("G", ["Gift", "Goat", "Glass"]),
    ("H", ["Hand", "Hen", "Hair"]),
    ("I", ["Ice cream", "Iron", "Insect"]),
    ("J", ["Jam", "Jacket", "Juice"]),
    ("K", ["Key", "King", "Kite"]),
    ("L", ["Lemon", "Lion", "Leg"]),
    ("M", ["Moon", "Monkey", "Man"]),
    ("N", ["Nose", "Nurse", "Nest"]),
    ("O", ["Orange", "Oil", "Olives"]),
    ("P", ["Plane", "Pen", "Pencil"]),
    ("Q", ["Queen", "Quarter", "Quiet"]),
    ("R", ["Ruler", "Rabbit", "Ring"]),
    ("S", ["Sun", "Snake", "Star"]),
    ("T", ["Tree", "Table", "Train"]),
    ("U", ["Umbrella", "Up", "Uncle"]),
    ("V", ["Vegetable", "Violin", "Vase"]),
    ("W", ["Watermelon", "Window", "Watch"]),
    ("X", ["X-ray", "Xylophone", "Box"]),
    ("Y", ["Yellow", "Yoyo", "Yacht"]),
    ("Z", ["Zoo", "Zebra", "Zipper"])
]

# Flat list of all vocabulary words and their sanitized SVG paths to use as distractors
all_words = []
for letter, words in alphabet_vocab:
    for w in words:
        all_words.append({
            "text": w,
            "image": f"assets/images/{w.lower().replace(' ', '_')}.svg"
        })

# Generator
for idx, (letter, words) in enumerate(alphabet_vocab, start=1):
    skill_id = f"english_3_s{idx}"
    filename = f"letter_{letter.lower()}.json"
    filepath = os.path.join("subjects/english/curriculum", filename)
    
    # Resolve Arabic/English title/instructions
    title_ar = f"حرف {letter}"
    title_en = f"Letter {letter}"
    instr_ar = f"هيا نتعلم ونلعب مع حرف {letter} الجميل! 🌟"
    instr_en = f"Let's learn and play with the beautiful letter {letter}! 🌟"
    
    questions = []
    
    # 1. 3 Multiple Choice Questions (one for each word)
    for w in words:
        image_path = f"assets/images/{w.lower().replace(' ', '_')}.svg"
        
        # Generate distractors (2 other random letters)
        letters_pool = [l for l, _ in alphabet_vocab if l != letter]
        distractors = random.sample(letters_pool, 2)
        options = [letter] + distractors
        random.shuffle(options)
        
        questions.append({
            "type": "multiple-choice",
            "question": "Which letter does this image start with?",
            "image": image_path,
            "options": options,
            "correct": letter
        })
        
    # 2. 3 Audio Choice Questions (one for each word)
    for w in words:
        correct_img_path = f"assets/images/{w.lower().replace(' ', '_')}.svg"
        
        # Select a distractor word from other letters
        distractor_pool = [item for item in all_words if item["text"] not in words]
        distractor = random.choice(distractor_pool)
        
        options = [
            {"text": w, "image": correct_img_path},
            {"text": distractor["text"], "image": distractor["image"]}
        ]
        random.shuffle(options)
        
        questions.append({
            "type": "audio-choice",
            "question": "Listen to the word and choose the matching picture! 🔊",
            "speak_text": w,
            "options": options,
            "correct": w
        })
        
    # 3. 1 Drag and Drop Question
    # Matches current letter, and if index > 1, matches current and previous letter
    items = [{"id": f"drag-{letter}", "text": letter}]
    targets = [{"id": f"drop-{letter.lower()}", "text": letter.lower(), "matches": f"drag-{letter}"}]
    
    if idx > 1:
        prev_letter, _ = alphabet_vocab[idx - 2]
        items.append({"id": f"drag-{prev_letter}", "text": prev_letter})
        targets.append({"id": f"drop-{prev_letter.lower()}", "text": prev_letter.lower(), "matches": f"drag-{prev_letter}"})
        
    # Shuffle drag items so they are not in the same order as drop targets
    random.shuffle(items)
    
    questions.append({
        "type": "drag-and-drop",
        "question": "Match the capital letters to their lowercase baskets!",
        "items": items,
        "targets": targets
    })
    
    # Save the JSON file
    level_data = {
        skill_id: {
            "id": skill_id,
            "age_group": 3,
            "subject": "english",
            "title_ar": title_ar,
            "title_en": title_en,
            "instructions_ar": instr_ar,
            "instructions_en": instr_en,
            "questions": questions
        }
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(level_data, f, indent=2, ensure_ascii=False)
        
print(f"Successfully generated 26 split curriculum JSON files in subjects/english/curriculum/")
