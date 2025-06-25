# @title 🔊 Giao diện tạo giọng nói + phụ đề chính xác đa ngôn ngữ
import os, re, requests
from pydub import AudioSegment
from datetime import datetime
from IPython.display import display, Audio, FileLink, clear_output
import ipywidgets as widgets
from google.colab import files

# ==== Giao diện ====
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
subtitle_limit = widgets.IntText(value=5, description='📜 SRT từ/ký tự dòng:')
lang_dropdown = widgets.Dropdown(
    options=[
        ("🇬🇧 English", "en"),
        ("🇯🇵 Japanese", "ja"),
        ("🇨🇳 Chinese", "zh"),
        ("🇰🇷 Korean", "ko"),
        ("🇻🇳 Vietnamese", "vi"),
        ("🇫🇷 French", "fr"),
        ("🇩🇪 German", "de"),
        ("🇮🇹 Italian", "it"),
        ("🇷🇺 Russian", "ru"),
        ("🇪🇸 Spanish", "es"),
    ],
    value="en",
    description='🌐 Ngôn ngữ phụ đề:'
)
text_stats = widgets.HTML(value="")
btn_generate = widgets.Button(description="🚀 Bắt đầu tạo giọng nói", button_style='success')

# ==== Tiện ích ====
def convert_time(t):
    ms = int((t - int(t)) * 1000)
    h, m, s = int(t // 3600), int(t % 3600 // 60), int(t % 60)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def ultra_split(text, max_unit=5, lang='en'):
    items = list(text.strip()) if lang in ['ja', 'zh', 'ko'] else text.strip().split()
    chunks, temp = [], []
    for item in items:
        temp.append(item)
        if len(temp) >= max_unit:
            chunks.append(''.join(temp) if lang in ['ja', 'zh', 'ko'] else ' '.join(temp))
            temp = []
    if temp:
        chunks.append(''.join(temp) if lang in ['ja', 'zh', 'ko'] else ' '.join(temp))
    return chunks

def split_text(text, maxlen=10000):
    sents = re.split(r'(?<=[.!?。！？])\s*', text)
    out, tmp = [], ""
    for s in sents:
        if len(tmp) + len(s) <= maxlen:
            tmp += s
        else:
            out.append(tmp.strip())
            tmp = s
    if tmp: out.append(tmp.strip())
    return out

def check_credit(api_key):
    try:
        r = requests.get("https://api.elevenlabs.io/v1/user", headers={"xi-api-key": api_key})
        return r.json()['subscription']['character_limit'] - r.json()['subscription']['character_count']
    except: return None

def gen_audio(text, api_key, voice_id, model_id, settings, outname):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    r = requests.post(url, headers={"xi-api-key": api_key, "Content-Type": "application/json"}, json={
        "text": text,
        "model_id": model_id,
        "voice_settings": settings
    })
    if r.status_code == 200:
        with open(outname, "wb") as f: f.write(r.content)
        return True
    else:
        try: return False, r.json().get("detail", {}).get("message", "Unknown error")
        except: return False, "Unknown error"

def generate_subtitles(paragraphs, folder="output_audio", file="output.srt", lang="en", unit=5):
    srt_path = os.path.join(folder, file)
    files = sorted([f for f in os.listdir(folder) if f.startswith("seg") and f.endswith(".mp3")])
    with open(srt_path, "w", encoding="utf-8") as srt:
        current_time, index = 0.0, 1
        for para, fname in zip(paragraphs, files):
            audio = AudioSegment.from_mp3(os.path.join(folder, fname))
            duration = audio.duration_seconds
            units = ultra_split(para, unit, lang)
            total_chars = sum(len(u) for u in units)
            for u in units:
                du = duration * (len(u) / total_chars)
                srt.write(f"{index}\n{convert_time(current_time)} --> {convert_time(current_time + du)}\n{u}\n\n")
                current_time += du
                index += 1
    return srt_path

# ==== Nút chính ====
def on_generate(b):
    clear_output()
    display(api_input, voice_id_input, text_input, model_dropdown,
            slider_stability, slider_similarity, slider_style, slider_speed,
            chk_boost, split_length, subtitle_limit, lang_dropdown, text_stats, btn_generate)

    apis = api_input.value.strip().splitlines()
    voice_id = voice_id_input.value.strip()
    fulltext = text_input.value.strip()
    lang = lang_dropdown.value
    paragraphs = split_text(fulltext, split_length.value)
    text_stats.value = f"<b>📊 Đoạn:</b> {len(paragraphs)} | <b>Ký tự:</b> {sum(len(p) for p in paragraphs):,}"

    print("🔍 Kiểm tra API:")
    credit_pool = []
    for i, key in enumerate(apis):
        credit = check_credit(key)
        credit_pool.append([key, credit])
        print(f"🔑 API #{i+1}: {credit:,} ký tự" if credit else f"❌ API #{i+1} lỗi")

    settings = {
        "stability": slider_stability.value,
        "similarity_boost": slider_similarity.value,
        "style": slider_style.value,
        "speed": slider_speed.value,
        "optimize_streaming_latency": 4 if chk_boost.value else 0
    }

    os.makedirs("output_audio", exist_ok=True)
    for f in os.listdir("output_audio"):
        if f.endswith(".mp3") or f.endswith(".srt"):
            os.remove(os.path.join("output_audio", f))

    all_audio = []
    for i, para in enumerate(paragraphs):
        print(f"\n📘 Đoạn {i+1}: {para[:40]}...")
        for j, (key, credit) in enumerate(credit_pool):
            if credit and len(para) <= credit:
                success = gen_audio(para, key, voice_id, model_dropdown.value, settings, f"output_audio/seg{i+1}.mp3")
                if success is True:
                    credit_pool[j][1] -= len(para)
                    display(Audio(filename=f"output_audio/seg{i+1}.mp3"))
                    break
                else:
                    print(f"❌ API #{j+1} lỗi: {success[1]}")
            if j == len(credit_pool) - 1:
                print("⛔ Không còn API đủ quota!")
                return

    combined = AudioSegment.from_mp3("output_audio/seg1.mp3")
    for f in sorted(os.listdir("output_audio"))[1:]:
        if f.startswith("seg") and f.endswith(".mp3"):
            combined += AudioSegment.from_mp3(os.path.join("output_audio", f))
    combined.export("output_audio/full.mp3", format="mp3")

    print("\n✅ Đã tạo file âm thanh:")
    display(Audio(filename="output_audio/full.mp3"))
    display(FileLink("output_audio/full.mp3", result_html_prefix="🎧 "))

    srt = generate_subtitles(paragraphs, folder="output_audio", file="output.srt", lang=lang, unit=subtitle_limit.value)
    print("✅ Đã tạo phụ đề:")
    display(FileLink(srt, result_html_prefix="📄 "))
    files.download(srt)

btn_generate.on_click(on_generate)

# ==== Hiển thị UI ====
display(api_input, voice_id_input, text_input, model_dropdown,
        slider_stability, slider_similarity, slider_style, slider_speed,
        chk_boost, split_length, subtitle_limit, lang_dropdown, text_stats, btn_generate)
