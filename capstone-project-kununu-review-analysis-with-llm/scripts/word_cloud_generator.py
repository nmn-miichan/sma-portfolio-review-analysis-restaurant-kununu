import json
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from pathlib import Path
import re
from collections import Counter
import random
import colorsys
from io import BytesIO

GERMAN_STOPWORDS = {
    'der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'einer', 'eines', 'einem', 'einen',
    'und', 'oder', 'aber', 'doch', 'dann', 'wenn', 'als', 'wie', 'so', 'auch', 'noch', 'nur',
    'schon', 'sehr', 'mehr', 'nach', 'vor', 'bei', 'mit', 'ohne', 'durch', 'für', 'gegen',
    'über', 'unter', 'zwischen', 'während', 'seit', 'bis', 'von', 'zu', 'an', 'auf', 'in',
    'ist', 'sind', 'war', 'waren', 'wird', 'werden', 'wurde', 'wurden', 'hat', 'haben',
    'hatte', 'hatten', 'kann', 'können', 'konnte', 'konnten', 'muss', 'müssen', 'musste',
    'sollte', 'sollen', 'wollte', 'wollen', 'würde', 'würden', 'könnte', 'könnten',
    'ich', 'du', 'er', 'sie', 'es', 'wir', 'ihr', 'man', 'sich', 'mich', 'dir', 'ihm',
    'uns', 'euch', 'ihnen', 'diesem', 'dieser', 'dieses', 'diese', 'jeder', 'jede', 'jedes',
    'alle', 'alles', 'viele', 'wenige', 'einige', 'andere', 'anderer', 'anderes',
    'dass', 'weil', 'damit', 'obwohl', 'während', 'bevor', 'nachdem', 'sobald'
}

def create_custom_color_function(color_scheme='critical'):
    def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
        word_seed = hash(word) % 1000
        random.seed(word_seed)
        if color_scheme == 'critical':
            hue = random.uniform(0, 20)
            saturation = random.uniform(0.6, 0.9)
            lightness = random.uniform(0.2, 0.6)
        else:
            hue = random.uniform(90, 150)
            saturation = random.uniform(0.6, 0.9)
            lightness = random.uniform(0.2, 0.6)
        r, g, b = colorsys.hls_to_rgb(hue/360, lightness, saturation)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    return color_func

def preprocess_text_for_wordcloud(text, min_word_length=3):
    text = text.lower()
    text = re.sub(r'[^\w\säöüß]', ' ', text)
    words = text.split()
    filtered_words = [
        word for word in words
        if len(word) >= min_word_length and word not in GERMAN_STOPWORDS and not word.isdigit()
    ]
    return ' '.join(filtered_words)

def extract_text_from_points(points_data, weight_by_frequency=True):
    combined_text = []
    for point in points_data:
        text = point['point']
        count = point['count']
        processed_text = preprocess_text_for_wordcloud(text)
        if weight_by_frequency:
            combined_text.extend([processed_text] * count)
        else:
            combined_text.append(processed_text)
    return ' '.join(combined_text)

def get_wordcloud_image(json_file_path, category, subcategory, width=800, height=600, max_words=100):
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except Exception:
        return None

    categories = data.get('categories', [])
    category_data = None
    for cat in categories:
        if category in cat:
            category_data = cat[category]
            break
    if not category_data or subcategory not in category_data:
        return None

    points_data = category_data[subcategory]
    text_for_wordcloud = extract_text_from_points(points_data, weight_by_frequency=True)
    if not text_for_wordcloud.strip():
        return None

    color_scheme = 'critical' if subcategory == 'critical_points' else 'positive'
    color_func = create_custom_color_function(color_scheme)
    try:
        wordcloud = WordCloud(
            width=width,
            height=height,
            max_words=max_words,
            background_color='white',
            color_func=color_func,
            stopwords=GERMAN_STOPWORDS,
            collocations=False,
            prefer_horizontal=0.7,
            min_word_length=3
        ).generate(text_for_wordcloud)
    except Exception:
        return None

    return wordcloud.to_image()
