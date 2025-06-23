# ✅ FULL CODE: Colab interface with persistent inputs and subtitle customization

import os, requests, re
from datetime import datetime
from pydub import AudioSegment
from IPython.display import display, Audio, clear_output, FileLink
import ipywidgets as widgets
from google.colab import files

# === UI Components ===
api_input = widgets.Textarea(
    value='',
    placeholder='Nhập các API key, mỗi dòng một key',
    description='🔑 API Key:',
    layout={'width': '100%', 'height': '100px'}
)

voice_id_input = widgets.Text(
    value='',
    placeholder='Nhập Voice ID',
    description='🗣️ Voice ID:',
    layout={'width': '100%'}
)

text_input = widgets.Textarea(
    value='',
    placeholder='Nhập văn bản cần tạo giọng...',
    description='📘 Văn bản:',
    layout={'width': '100%', 'height': '200px'}
)

model_dropdown = widgets.Dropdown(
    options=[
        ("Eleven Multilingual v2", "eleven_multilingual_v2"),
        ("Eleven Flash v2.5", "eleven_flash_v2_5"),
        ("Eleven Turbo v2.5", "eleven_turbo_v2_5"),
    ],
    value="eleven_flash_v2_5",
    description='🎷 Model:'
)

slider_stability = widgets.FloatSlider(value=0.3, min=0, max=1.0, step=0.05, description='🔧 Stability')
slider_similarity = widgets.FloatSlider(value=0.75, min=0, max=1.0, step=0.05, description='🎛️ Similarity')
slider_style = widgets.FloatSlider(value=0.0, min=0, max=1.0, step=0.05, description='🎨 Style')
slider_speed = widgets.FloatSlider(value=1.0, min=0.5, max=2.0, step=0.1, description='⏩ Speed')
chk_boost = widgets.Checkbox(value=False, description='⚡ Optimize Streaming')

split_length = widgets.IntText(value=10000, description='✂️ Split limit:')
subtitle_word_limit = widgets.IntText(value=5, description='📜 SRT từ/dòng:')
text_stats = widgets.HTML(value="", placeholder='Tông tin văn bản sẽ hiển thị ở đây...')

btn_generate = widgets.Button(description="🚀 Bắt đầu tạo giọng nói", button_style='success')

# === Utility Functions ===
def convert_seconds_to_srt_time(seconds):
    millisec = int((seconds - int(seconds)) * 1000)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02}:{m:02}:{s:02},{millisec:03}"

def ultra_split_sentences(paragraph, max_words=5):
    words = paragraph.strip().split()
    chunks, temp = [], []
    for word in words:
        temp.append(word)
        if len(temp) >= max_words:
            chunks.append(' '.join(temp))
            temp = []
    if temp:
        chunks.append(' '.join(temp))
    return chunks

def split_into_lines(text, max_line_length=28):
    words = text.split()
    line = ""
    for word in words:
        if len(line + " " + word) <= max_line_length:
            line += (" " if line else "") + word
        else:
            break
    return line

def split_text_into_paragraphs(text, max_length=10000):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""
    for s in sentences:
        if len(current) + len(s) + 1 <= max_length:
            current += s + " "
        else:
            chunks.append(current.strip())
            current = s + " "
    if current:
        chunks.append(current.strip())
    return chunks

def generate_subtitle(paragraphs, folder="output_audio", subtitle_file="full_output.srt", word_per_line=5):
    files = sorted([f for f in os.listdir(folder) if f.startswith("voice_row") and f.endswith(".mp3")])
    output_path = os.path.join(folder, subtitle_file)
    with open(output_path, "w", encoding="utf-8") as srt:
        current_time = 0.0
        subtitle_index = 1
        for para, file in zip(paragraphs, files):
            audio = AudioSegment.from_mp3(os.path.join(folder, file))
            duration = audio.duration_seconds
            sentence_groups = ultra_split_sentences(para, max_words=word_per_line)
            total_chars = sum(len(s) for s in sentence_groups)
            for sentence in sentence_groups:
                sentence_duration = duration * (len(sentence) / total_chars)
                start = convert_seconds_to_srt_time(current_time)
                end = convert_seconds_to_srt_time(current_time + sentence_duration)
                srt.write(f"{subtitle_index}\n{start} --> {end}\n{split_into_lines(sentence)}\n\n")
                current_time += sentence_duration
                subtitle_index += 1
    return output_path

def generate_voice(text, api_key, voice_id, model_id, stability, similarity_boost, style, speed, optimize):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "speed": speed,
            "optimize_streaming_latency": 4 if optimize else 0
        }
    }
    r = requests.post(url, headers=headers, json=payload)
    if r.status_code == 200:
        fname = f"voice_{hash(text)%100000}.mp3"
        outpath = os.path.join("output_audio", fname)
        with open(outpath, "wb") as f:
            f.write(r.content)
        return True, fname
    else:
        try:
            err = r.json().get("detail", {}).get("message", "Lỗi không xác định")
        except:
            err = "Lỗi không xác định"
        return False, err

def check_api_credits(api_key):
    try:
        r = requests.get("https://api.elevenlabs.io/v1/user", headers={"xi-api-key": api_key})
        if r.status_code == 200:
            data = r.json()['subscription']
            return data['character_limit'] - data['character_count']
    except:
        return None

def on_generate_clicked(b):
    clear_output()
    display(api_input, voice_id_input, text_input, model_dropdown,
            slider_stability, slider_similarity, slider_style, slider_speed,
            chk_boost, split_length, subtitle_word_limit, text_stats, btn_generate)

    try:
        api_keys = api_input.value.strip().splitlines()
        voice_id = voice_id_input.value.strip()
        full_text = text_input.value.strip()
        paragraphs = split_text_into_paragraphs(full_text, max_length=split_length.value)
    except:
        print("❌ Dữ liệu nhập thiếu hoặc lỗi!")
        return

    total_chars = sum(len(p) for p in paragraphs)
    text_stats.value = f"<b>📊 Tổng đoạn:</b> {len(paragraphs)} | <b>Tổng ký tự:</b> {total_chars:,}"

    print("🔍 Tín dụng các API:")
    api_credits = []
    for i, key in enumerate(api_keys):
        credit = check_api_credits(key)
        api_credits.append((key, credit))
        print(f"🔑 API #{i+1}: {credit:,} ký tự còn lại" if credit else f"🔑 API #{i+1}: ❌ lỗi")

    model_id = model_dropdown.value
    stability, similarity, style, speed, optimize = slider_stability.value, slider_similarity.value, slider_style.value, slider_speed.value, chk_boost.value

    out_dir = "output_audio"
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        if f.endswith(".mp3") or f.endswith(".srt"):
            os.remove(os.path.join(out_dir, f))

    audios = []
    for i, para in enumerate(paragraphs):
        print(f"📘 Đoạn {i+1}: {para.strip()[:60]}...")
        used_api = None
        for j, (key, credit) in enumerate(api_credits):
            if credit and len(para) <= credit:
                success, result = generate_voice(para, key, voice_id, model_id, stability, similarity, style, speed, optimize)
                if success:
                    api_credits[j] = (key, credit - len(para))
                    newname = f"voice_row{i+1}.mp3"
                    filepath = os.path.join(out_dir, newname)
                    os.rename(os.path.join(out_dir, result), filepath)
                    audio = AudioSegment.from_mp3(filepath)
                    audios.append(audio)
                    display(Audio(filename=filepath))
                    used_api = j+1
                    print(f"➡️ Sử dụng API #{used_api}\n")
                    break
                else:
                    print(f"❌ API #{j+1} lỗi: {result}")
        if used_api is None:
            print(f"⛔ Không API nào đủ quota cho đoạn này\n")
            return

    if audios:
        output_mp3 = os.path.join(out_dir, "full_output.mp3")
        combined = audios[0]
        for a in audios[1:]:
            combined += a
        combined.export(output_mp3, format="mp3")
        print("\n✅ Đã gộp file: full_output.mp3")
        display(Audio(filename=output_mp3))
        display(FileLink(output_mp3, result_html_prefix="📅 Tải MP3: "))

    srt_path = generate_subtitle(paragraphs, folder=out_dir, word_per_line=subtitle_word_limit.value)
    print("\n✅ Đã tạo phụ đề:")
    display(FileLink(srt_path, result_html_prefix="📅 Tải SRT: "))
    files.download(srt_path)

btn_generate.on_click(on_generate_clicked)

# === Show UI ===
display(api_input, voice_id_input, text_input, model_dropdown,
        slider_stability, slider_similarity, slider_style, slider_speed,
        chk_boost, split_length, subtitle_word_limit, text_stats, btn_generate)
