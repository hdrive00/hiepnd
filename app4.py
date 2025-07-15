from IPython.display import display, HTML, clear_output, Audio
import ipywidgets as widgets
import requests
import os
import re
import zipfile
from pydub import AudioSegment
import traceback
import base64
from IPython.display import Javascript
import time

# ========================== #
# 🔉 Hàm gọi API ElevenLabs
# ========================== #
def generate_voice(text, api_key, voice_id, model_version, stability=0.3, similarity=0.75, style=None, speed=None, speaker_boost=True):
    # Xác định model dựa trên phiên bản đã chọn
    models = {
        "Zilankhulo zambiri v2": "eleven_multilingual_v2",
        "Zilankhulo zambiri v2": "eleven_v3",
        "Turbo v2.5": "eleven_turbo_v2"
    }
    model_id = models.get(model_version, "eleven_multilingual_v2")
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }

    voice_settings = {
        "stability": float(stability),
        "similarity_boost": float(similarity),
        "use_speaker_boost": bool(speaker_boost)
    }

    if style is not None and 0.0 <= style <= 1.0:
        voice_settings["style"] = float(style)
    if speed is not None and 0.5 <= speed <= 2.0:
        voice_settings["speed"] = float(speed)

    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": voice_settings
    }

    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload)
        elapsed_time = time.time() - start_time
        
        if response.status_code != 200:
            error_msg = f"Lỗi API ({response.status_code}): "
            try:
                error_data = response.json()
                error_msg += error_data.get('detail', {}).get('message', 'Unknown error')
            except:
                error_msg += response.text[:200]
            print(error_msg)
            
            if response.status_code == 401:
                print("\n⚠️ QUAN TRỌNG: API key của bạn có thể đã bị chặn")
                print("→ Giải pháp: Tạo API key mới hoặc nâng cấp tài khoản trả phí")
            
            return None
            
        print(f"✅ Tạo thành công trong {elapsed_time:.2f}s")
        return response.content
    except Exception as e:
        print(f"Lỗi kết nối: {str(e)}")
        return None

# ========================== #
# 📊 Lấy thông tin credits
# ========================== #
def get_credits(api_key):
    try:
        res = requests.get("https://api.elevenlabs.io/v1/user", headers={"xi-api-key": api_key})
        if res.status_code == 200:
            data = res.json().get("subscription", {})
            return data.get("character_limit", 0) - data.get("character_count", 0)
        else:
            print(f"Lỗi khi lấy credit: {res.status_code} - {res.text[:200]}")
            return None
    except Exception as e:
        print(f"Lỗi kết nối khi lấy credit: {str(e)}")
        return None

# ========================== #
# 📝 Tự động tách đoạn < max_chars
# ========================== #
def split_text_to_blocks(text, max_chars=5000):
    cleaned_text = re.sub(r'[^\w\s.,!?;:\'"-]', '', text.strip())
    
    sentences = re.split(r'(?<=[.!?])\s+', cleaned_text)
    blocks = []
    current_block = ""

    for sentence in sentences:
        if len(current_block) + len(sentence) + 1 <= max_chars:
            current_block += sentence + " "
        else:
            if current_block:
                blocks.append(current_block.strip())
            current_block = sentence + " "
    if current_block:
        blocks.append(current_block.strip())
    return blocks

# ========================== #
# 🗜️ Tạo file ZIP
# ========================== #
def create_zip(files, zip_filename="voices.zip"):
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for file in files:
            if os.path.exists(file):
                zipf.write(file, os.path.basename(file))
    return zip_filename

# ========================== #
# 🔊 Gộp file âm thanh
# ========================== #
def merge_audio_files(files, output_file="merged_voice.mp3"):
    combined = AudioSegment.empty()
    for file in files:
        sound = AudioSegment.from_mp3(file)
        combined += sound
    combined.export(output_file, format="mp3")
    return output_file

# ========================== #
# 🚀 Chạy xử lý
# ========================== #
def run_tool(api_keys, voice_id, model_version, text_raw, st, sm, sty, spd, boost, max_chars):
    api_keys = [key.strip() for key in api_keys.splitlines() if key.strip()]
    voice_id = voice_id.strip()
    text_raw = text_raw.strip()
    
    if not api_keys or not voice_id or not text_raw:
        print("❌ Vui lòng nhập đầy đủ thông tin")
        return None
    
    print("🔐 Tín dụng còn lại:")
    credit_list = []
    for key in api_keys:
        r = get_credits(key)
        if r is None:
            print(f"- {key[:6]}...: lỗi")
        else:
            print(f"- {key[:6]}...: {r}")
        credit_list.append((key, r))

    texts = split_text_to_blocks(text_raw, max_chars)
    print(f"\n📄 Phát hiện {len(texts)} đoạn văn cần xử lý.")
    
    # Hiển thị thông tin phiên bản đã chọn
    model_info = {
        "Zilankhulo zambiri v2": "Đa ngôn ngữ, chất lượng cao",
        "Flash v2.5": "Tốc độ cực nhanh, độ trễ thấp",
        "Turbo v2.5": "Cân bằng giữa tốc độ và chất lượng"
    }
    print(f"⚡ Phiên bản: {model_version} - {model_info[model_version]}\n")
    
    os.makedirs("voices", exist_ok=True)
    generated_files = []

    for i, text in enumerate(texts):
        used = False
        print(f"⏳ Đang xử lý đoạn {i+1}/{len(texts)}...")
        for key, r in credit_list:
            if r is None or r <= 0:
                continue
                
            print(f"  Sử dụng API key: {key[:6]}...")
            audio = generate_voice(text, key, voice_id, model_version, st, sm, sty, spd, boost)
            
            if audio:
                fname = f"voices/voice_{i+1}.mp3"
                with open(fname, "wb") as f:
                    f.write(audio)
                print(f"✅ Đoạn {i+1} tạo thành công!")
                display(Audio(fname))
                generated_files.append(fname)
                used = True
                break
                
        if not used:
            print(f"❌ Đoạn {i+1} lỗi: không có API hoạt động hoặc tạo thất bại.")
            print("  → Gợi ý khắc phục:")
            print("    1. Kiểm tra lại Voice ID")
            print("    2. Giảm Stability/Similarity")
            print("    3. Tạo API key mới hoặc nâng cấp tài khoản")
    
    return generated_files

# ========================== #
# 🎨 Tạo giao diện đẹp
# ========================== #
# CSS tùy chỉnh
style_css = """
<style>
    .main-container {
        max-width: 800px;
        margin: 20px auto;
        padding: 20px;
        border-radius: 15px;
        background: linear-gradient(135deg, #1a2a6c, #b21f1f, #1a2a6c);
        color: white;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    .header {
        text-align: center;
        padding: 15px;
        margin-bottom: 20px;
        background: rgba(0,0,0,0.3);
        border-radius: 10px;
        border-bottom: 2px solid #ffcc00;
    }
    
    .section {
        background: rgba(0,0,0,0.2);
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .section-title {
        font-size: 18px;
        font-weight: bold;
        margin-bottom: 15px;
        color: #ffcc00;
        display: flex;
        align-items: center;
    }
    
    .section-title i {
        margin-right: 10px;
        font-size: 24px;
    }
    
    .input-field {
        width: 100%;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #444;
        background: rgba(0,0,0,0.3);
        color: white;
        margin-bottom: 10px;
        font-size: 14px;
    }
    
    .slider-container {
        padding: 10px;
        background: rgba(0,0,0,0.2);
        border-radius: 8px;
        margin-bottom: 10px;
    }
    
    .btn-run {
        background: linear-gradient(to right, #ff8c00, #ffcc00);
        color: #1a1a1a;
        border: none;
        padding: 12px 25px;
        font-size: 16px;
        font-weight: bold;
        border-radius: 50px;
        cursor: pointer;
        transition: all 0.3s;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        display: block;
        margin: 20px auto;
        width: 200px;
    }
    
    .btn-run:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
    }
    
    .btn-download {
        background: linear-gradient(to right, #4CAF50, #8BC34A);
        color: white;
        border: none;
        padding: 10px 20px;
        font-size: 14px;
        font-weight: bold;
        border-radius: 5px;
        cursor: pointer;
        transition: all 0.3s;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        margin: 5px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
    }
    
    .btn-download:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
    }
    
    .download-container {
        background: rgba(0,0,0,0.3);
        padding: 15px;
        border-radius: 10px;
        margin-top: 20px;
        text-align: center;
    }
    
    .download-title {
        font-size: 16px;
        font-weight: bold;
        margin-bottom: 10px;
        color: #ffcc00;
    }
    
    .footer {
        text-align: center;
        margin-top: 20px;
        font-size: 12px;
        color: rgba(255,255,255,0.6);
    }
    
    .credits {
        display: flex;
        justify-content: space-between;
        margin-top: 10px;
    }
    
    .credit-item {
        background: rgba(0,0,0,0.3);
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        flex: 1;
        margin: 0 5px;
    }
    
    .instructions {
        background: rgba(0,0,0,0.3);
        padding: 15px;
        border-radius: 10px;
        margin-top: 20px;
        font-size: 13px;
    }
    
    .instructions ul {
        padding-left: 20px;
        margin: 10px 0;
    }
    
    .instructions li {
        margin-bottom: 8px;
    }
    
    .download-link {
        display: block;
        padding: 10px;
        background: #4CAF50;
        color: white;
        text-align: center;
        border-radius: 5px;
        margin: 10px 0;
        text-decoration: none;
        font-weight: bold;
    }
    
    .download-link:hover {
        background: #45a049;
    }
    
    .model-selector {
        display: flex;
        justify-content: space-between;
        margin: 15px 0;
    }
    
    .model-option {
        flex: 1;
        padding: 12px;
        margin: 0 5px;
        text-align: center;
        background: rgba(0,0,0,0.3);
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.3s;
        border: 2px solid transparent;
    }
    
    .model-option:hover {
        background: rgba(0,0,0,0.4);
    }
    
    .model-option.selected {
        background: rgba(255,204,0,0.2);
        border: 2px solid #ffcc00;
    }
    
    .model-option h4 {
        margin: 5px 0;
        color: #ffcc00;
    }
    
    .model-option p {
        font-size: 12px;
        margin: 5px 0;
        color: #ccc;
    }
    
    .progress-container {
        height: 10px;
        background: rgba(255,255,255,0.1);
        border-radius: 5px;
        margin: 10px 0;
        overflow: hidden;
    }
    
    .progress-bar {
        height: 100%;
        background: linear-gradient(to right, #ff8c00, #ffcc00);
        border-radius: 5px;
        transition: width 0.3s;
    }
    
    .status-text {
        text-align: center;
        font-size: 14px;
        margin: 10px 0;
        color: #ffcc00;
    }
</style>
"""

# Tạo các widget
api_input = widgets.Textarea(
    placeholder="Nhập API keys (mỗi key trên một dòng)",
    layout={'width': '100%', 'height': '100px'},
    style={'description_width': 'initial'}
)

voice_input = widgets.Text(
    placeholder="Nhập Voice ID",
    layout={'width': '100%'}
)

text_input = widgets.Textarea(
    placeholder="Nhập văn bản cần chuyển đổi...",
    layout={'width': '100%', 'height': '150px'}
)

stability = widgets.FloatSlider(
    value=0.3, min=0.0, max=1.0, step=0.05, 
    description='Stability:',
    style={'description_width': '120px'},
    layout={'width': '95%'}
)

similarity = widgets.FloatSlider(
    value=0.75, min=0.0, max=1.0, step=0.05, 
    description='Similarity:',
    style={'description_width': '120px'},
    layout={'width': '95%'}
)

style_slider = widgets.FloatSlider(
    value=0.0, min=0.0, max=1.0, step=0.05, 
    description='Style:',
    style={'description_width': '120px'},
    layout={'width': '95%'}
)

speed = widgets.FloatSlider(
    value=1.0, min=0.5, max=2.0, step=0.05, 
    description='Speed:',
    style={'description_width': '120px'},
    layout={'width': '95%'}
)

boost = widgets.Checkbox(
    value=True, 
    description='Use Speaker Boost',
    style={'description_width': 'initial'}
)

max_chars = widgets.IntText(
    value=5000, 
    description="Kí tự tối đa/đoạn:",
    style={'description_width': 'initial'}
)

# Tạo nút bấm
run_btn = widgets.Button(
    description="🎧 Tạo giọng nói",
    button_style='success',
    layout={'width': '200px', 'margin': '20px auto'},
    style={'font_weight': 'bold', 'font_size': '16px'}
)

# Tạo container cho nút tải về
download_container = widgets.Output()

output = widgets.Output()

# Tạo model selector
model_versions = ["Zilankhulo zambiri v2", "Flash v2.5", "Turbo v2.5"]
selected_model = widgets.RadioButtons(
    options=model_versions,
    value=model_versions[0],
    layout={'width': '100%'},
    style={'description_width': 'initial'}
)

# Hàm tải file bằng JavaScript
def create_download_link(filename):
    with open(filename, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    
    display(HTML(
        f'<a class="download-link" href="data:application/octet-stream;base64,{b64}" download="{filename}">'
        f'📥 Tải file {os.path.basename(filename)}'
        '</a>'
    ))

# Sự kiện khi nhấn nút
def on_run_click(b):
    with output:
        clear_output()
        try:
            # Tạo thanh tiến trình
            progress_html = """
            <div class="progress-container">
                <div class="progress-bar" id="progress-bar" style="width: 0%"></div>
            </div>
            <div class="status-text" id="status-text">Đang chuẩn bị...</div>
            """
            display(HTML(progress_html))
            
            # Hàm cập nhật tiến trình
            def update_progress(percent, message):
                display(Javascript(f"""
                    document.getElementById('progress-bar').style.width = '{percent}%';
                    document.getElementById('status-text').innerText = '{message}';
                """))
            
            update_progress(10, "Đang kiểm tra API keys...")
            generated_files = run_tool(
                api_input.value,
                voice_input.value,
                selected_model.value,
                text_input.value,
                st=stability.value,
                sm=similarity.value,
                sty=style_slider.value,
                spd=speed.value,
                boost=boost.value,
                max_chars=max_chars.value
            )
            
            update_progress(80, "Đang tạo file kết quả...")
            # Hiển thị nút tải về nếu có file được tạo
            if generated_files:
                # Tạo file ZIP
                zip_file = create_zip(generated_files)
                
                # Tạo file gộp nếu có nhiều file
                if len(generated_files) > 1:
                    merged_file = merge_audio_files(generated_files)
                
                with download_container:
                    clear_output()
                    # Hiển thị nút tải về
                    display(widgets.HTML("<div class='download-title'>TẢI KẾT QUẢ:</div>"))
                    
                    # Tạo liên kết tải file ZIP
                    create_download_link(zip_file)
                    
                    # Tạo liên kết tải file gộp nếu có
                    if len(generated_files) > 1:
                        create_download_link(merged_file)
                    
                    # Hướng dẫn thêm
                    display(widgets.HTML(
                        "<div style='margin-top:10px; color:#ffcc00;'>"
                        "<b>HƯỚNG DẪN TẢI FILE:</b><br>"
                        "Nhấn vào liên kết bên trên để tải file"
                        "</div>"
                    ))
            
            update_progress(100, "Hoàn thành!")
            
        except Exception as e:
            print("❌ Lỗi xảy ra:", e)
            import traceback
            traceback.print_exc()
            update_progress(0, "Đã xảy ra lỗi!")

# Gán sự kiện cho nút run_btn
run_btn.on_click(on_run_click)

# Hiển thị giao diện
display(HTML(style_css))

# Tạo model selector HTML
model_selector_html = f"""
<div class="model-selector">
    <div class="model-option {'selected' if selected_model.value == 'Zilankhulo zambiri v2' else ''}" onclick="selectModel('Zilankhulo zambiri v2')">
        <h4>Zilankhulo zambiri v2</h4>
        <p>Đa ngôn ngữ, chất lượng cao</p>
    </div>
    <div class="model-option {'selected' if selected_model.value == 'Flash v2.5' else ''}" onclick="selectModel('Flash v2.5')">
        <h4>Flash v2.5</h4>
        <p>Tốc độ cực nhanh, độ trễ thấp</p>
    </div>
    <div class="model-option {'selected' if selected_model.value == 'Turbo v2.5' else ''}" onclick="selectModel('Turbo v2.5')">
        <h4>Turbo v2.5</h4>
        <p>Cân bằng giữa tốc độ và chất lượng</p>
    </div>
</div>

<script>
function selectModel(model) {{
    var options = document.querySelectorAll('.model-option');
    options.forEach(function(option) {{
        option.classList.remove('selected');
    }});
    
    event.currentTarget.classList.add('selected');
    
    // Gửi giá trị đã chọn về Python
    var kernel = IPython.notebook.kernel;
    kernel.execute("selected_model.value = '" + model + "'");
}}
</script>
"""

main_container = widgets.VBox([
    widgets.HTML("""
    <div class="main-container">
        <div class="header">
            <h1>🔊 ElevenLabs Voice Generator</h1>
            <p>Công cụ chuyển văn bản thành giọng nói chất lượng cao</p>
        </div>
        
        <div class="section">
            <div class="section-title"><i>🔑</i> Thông tin tài khoản</div>
            <label>API Keys (mỗi key trên một dòng):</label>
    """),
    api_input,
    widgets.HTML("""
            <label>Voice ID:</label>
    """),
    voice_input,
    widgets.HTML("""
        </div>
        
        <div class="section">
            <div class="section-title"><i>⚙️</i> Chọn phiên bản</div>
    """),
    widgets.HTML(model_selector_html),
    widgets.HTML("""
        </div>
        
        <div class="section">
            <div class="section-title"><i>📝</i> Nội dung văn bản</div>
    """),
    text_input,
    widgets.HTML("""
        </div>
        
        <div class="section">
            <div class="section-title"><i>🎚️</i> Thiết lập giọng nói</div>
            <div class="credits">
                <div class="credit-item">
                    <div>Stability</div>
                    <div style="font-size:24px;color:#ffcc00">""" + str(stability.value) + """</div>
                    <div>Độ ổn định giọng</div>
                </div>
                <div class="credit-item">
                    <div>Similarity</div>
                    <div style="font-size:24px;color:#ffcc00">""" + str(similarity.value) + """</div>
                    <div>Độ giống giọng gốc</div>
                </div>
                <div class="credit-item">
                    <div>Max Chars</div>
                    <div style="font-size:24px;color:#ffcc00">""" + str(max_chars.value) + """</div>
                    <div>Ký tự tối đa</div>
                </div>
            </div>
            
            <div class="slider-container">
    """),
    stability,
    similarity,
    style_slider,
    speed,
    boost,
    max_chars,
    widgets.HTML("""
            </div>
        </div>
        
        <div class="instructions">
            <p><strong>Hướng dẫn sử dụng:</strong></p>
            <ul>
                <li>API Keys: Nhập một hoặc nhiều API key từ ElevenLabs (mỗi key trên một dòng)</li>
                <li>Voice ID: Nhập ID giọng nói bạn muốn sử dụng</li>
                <li>Văn bản: Nhập nội dung bạn muốn chuyển thành giọng nói</li>
                <li>Điều chỉnh các thông số giọng nói theo ý muốn</li>
                <li>Nhấn nút "Tạo giọng nói" để bắt đầu quá trình chuyển đổi</li>
                <li>Sau khi hoàn thành, nhấn vào liên kết tải file để lưu kết quả</li>
            </ul>
            
            <p><strong>Lưu ý quan trọng:</strong></p>
            <ul>
                <li>Nếu gặp lỗi 401: API key của bạn có thể đã bị chặn</li>
                <li>Giải pháp: Tạo API key mới hoặc nâng cấp tài khoản trả phí</li>
            </ul>
        </div>
    """),
    
    # Nút chạy chính
    run_btn,
    
    # Khu vực kết quả
    output,
    
    # Khu vực tải về
    widgets.HTML("""
        <div class="download-container">
            <div class="download-title">TẢI KẾT QUẢ</div>
            <p>Kết quả sẽ xuất hiện tại đây sau khi hoàn thành</p>
        </div>
    """),
    download_container,
    
    widgets.HTML("""
        <div class="footer">
            <p>Công cụ được phát triển bởi ElevenLabs API | © 2023</p>
        </div>
    </div>
    """),
], layout={'align_items': 'center'})

display(main_container)
