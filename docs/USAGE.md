# doc2video 使用教程

## 一、环境准备

### 1. 系统依赖

**ffmpeg**（必须）：
```bash
# macOS
brew install ffmpeg
# Ubuntu/Debian
sudo apt install ffmpeg
```

**中文字体**：
- macOS：系统自带（PingFang / STHeiti），无需额外操作
- Linux：`sudo apt install fonts-noto-cjk` 或用 `--font` 指定
- 也可用 `--font /path/to/font.otf` 指定任意字体

### 2. Python 依赖

```bash
cd doc2video
pip install -r requirements.txt
```

### 3. TTS 后端（二选一）

#### 方式 A：edge_tts（免费，最快上手）

无需任何服务，联网即可用。`--tts edge` 触发。

#### 方式 B：qwen3_local（本地服务，音质更好）

需要本地跑一个 OpenAI 兼容的 TTS 服务（默认 `http://127.0.0.1:8001/v1/audio/speech`，body 格式 `{mode, text, instruction, ...}`，返回 WAV）。参考实现：Qwen3TTS_MLX。

启动服务后用 `--tts qwen3_local` 触发（这是默认值）。

---

## 二、准备素材

### 1. 截图来源

**方式 A：图文教程 HTML**

如果你的教程是 HTML（截图以 base64 嵌入），直接：
```bash
--html 教程.html
```
脚本会自动提取所有 base64 图片，按顺序作为截图。

**方式 B：截图目录**

把截图（.jpg/.png）放到一个目录，按文件名排序：
```bash
--shots /path/to/screenshots/
```

### 2. 文案

写一个 txt，**每行一段**，每段对应一个画面：
```
第一段解说词。
第二段解说词。
第三段。
```

文案建议：短视频风格，每段 15–25 字，节奏利落。

### 3. BGM（可选）

任意 mp3/m4a/wav。建议轻快、不抢戏的纯音乐。

---

## 三、生成视频

### 最简（edge_tts，无 BGM）

```bash
python make_promo_video.py \
  --html 教程.html \
  --script 文案.txt \
  --tts edge \
  -o out.mp4
```

### 完整（qwen3_local + BGM + 加速）

```bash
python make_promo_video.py \
  --html 教程.html \
  --script 文案.txt \
  --bgm bgm.mp3 \
  --tts qwen3_local \
  --speed 1.25 \
  --bgm-volume 0.18 \
  -o out.mp4
```

脚本会依次输出：
```
📸 [1/5] 准备截图...   提取 N 张
📝 [2/5] 文案 X 字, N 段
🔊 [3/5] TTS 配音...   模型耗时 Y s
🖼️ [4/5] 生成字幕帧...
🎬 [5/5] 合成视频 + BGM...
✅ 完成: out.mp4 (Z.Zs)
```

---

## 四、进阶：图文精准对应（mapping）

默认按文案段顺序轮播截图（第 1 段配第 1 张图）。但常出现"说到导出按钮了，画面还在安装步骤"。

用 `--mapping` 精准指定每段用哪张截图：

**mapping.json：**
```json
[[6], [9], [6], [7], [8,9], [9]]
```

含义：第 1 段用第 6 张截图、第 2 段用第 9 张、第 5 段用第 8 和第 9 张（快切）……

```bash
python make_promo_video.py \
  --html 教程.html --script 文案.txt \
  --mapping mapping.json \
  -o out.mp4
```

**怎么知道第几张截图是什么？** 看脚本运行时提取的截图（默认在 `/tmp/doc2video_work/shots_raw/`），或在 HTML 里截图按出现顺序编号。

---

## 五、调参建议

| 想要 | 参数 |
|------|------|
| 语速更快 | `--speed 1.35`（qwen3_local）或 `--rate +25%`（edge） |
| BGM 更小 | `--bgm-volume 0.12` |
| 换音色 | `--instruction "低沉浑厚纪录片男声"`（qwen3_local）或 `--voice zh-CN-YunxiNeural`（edge） |
| 竖屏（抖音） | 暂不支持（默认 1920×1080 横屏），可改 `make_frames` 的 size |
| 字幕样式 | 改 `make_frames` 里的 `font_size` / `stroke` |

---

## 六、常见问题

**Q: 报错"找不到中文字���"**
A: 用 `--font /path/to/font.otf` 指定。macOS 可用 `/System/Library/Fonts/STHeiti Medium.ttc`。

**Q: qwen3_local 报错连接失败**
A: 确认本地 TTS 服务在跑（默认 8001 端口）。或切 `--tts edge`。

**Q: 视频没声音**
A: 检查 `voice.wav` 是否生成（在 workdir）。TTS 失败时会报错。

**Q: 字幕显示方块**
A: 字体不支持中文。换字体或装中文字体。
