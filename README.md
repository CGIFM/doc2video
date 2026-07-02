# doc2video

> 把图文教程/截图 + 文案 → 推广短视频（自动配音、字幕、BGM）

一行命令把「使用文档」变成「带配音的演示短视频」。适合浏览器扩展、SaaS 工具、开源项目推广物料的快速产出。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📥 输入 → 📺 输出

**输入：**
- 截图来源（二选一）：
  - `--html`：图文教程 HTML（自动提取 base64 嵌入的截图）
  - `--shots`：截图目录（jpg/png）
- `--script`：文案 txt（每行一段，对应一个画面）
- `--bgm`（可选）：背景音乐 mp3/m4a
- TTS 后端：`qwen3_local`（本地服务，音质好）或 `edge_tts`（免费联网）

**输出：** mp4 视频（截图轮播 + 配音 + 烧入字幕 + 可选 BGM ducking）

## ✅ 能做什么 / ❌ 不能做什么

**能：**
- 从图文教程 HTML 一键提取 base64 截图
- TTS 配音（本地 Qwen3-TTS 或免费 edge_tts）
- 字幕烧入（按文案段分配时长，图文同步）
- 配音加速（atempo 保持音调，短视频节奏）
- BGM 混音（配音为主，BGM 可控音量）
- 图文精准对应（`--mapping` 配置每段用哪张截图）

**不能：**
- 真实操作录屏（只处理已有截图，不操作浏览器）
- LLM 生成文案（需自己提供 `--script`，或用别的工具生成）
- 复杂转场特效（简单硬切）

## 🔧 依赖

**必需：**
- Python 3.10+
- ffmpeg + ffprobe（系统���装：`brew install ffmpeg` / `apt install ffmpeg`）
- 中文字体（macOS 自带；Linux 装 `fonts-noto-cjk` 或 `fonts-wqy-microhei`；或 `--font` 指定）

**Python 包：** 见 [requirements.txt](requirements.txt)

**TTS（二选一）：**
- `qwen3_local`：需本地跑 Qwen3-TTS 服务（默认 `http://127.0.0.1:8001/v1/audio/speech`，OpenAI 兼容）。音质好，完全离线。参考实现：Qwen3TTS_MLX。
- `edge_tts`：免费、联网、开箱即用（微软 Edge 朗读接口）。

## 🚀 快速开始

```bash
git clone https://github.com/CGIFM/doc2video.git
cd doc2video
pip install -r requirements.txt

# 方式 A：edge_tts（无需本地服务，最快上手）
python make_promo_video.py \
  --html 你的教程.html \
  --script 文案.txt \
  --tts edge \
  -o out.mp4

# 方式 B：qwen3_local（音质更好，需 8001 服务在跑）
python make_promo_video.py \
  --html 你的教程.html \
  --script 文案.txt \
  --bgm bgm.mp3 \
  --tts qwen3_local \
  -o out.mp4
```

详细用法见 [docs/USAGE.md](docs/USAGE.md)。

## ⚙️ 参数

| 参数 | 说明 | 默认 |
|------|------|------|
| `--html` | 图文教程 HTML（提取 base64 截图） | - |
| `--shots` | 截图目录（与 --html 二选一） | - |
| `--script` | 文案 txt（每行一段） | **必填** |
| `--bgm` | 背景音乐 | - |
| `--tts` | `qwen3_local` / `edge` | `qwen3_local` |
| `--tts-url` | qwen3_local 服务地址 | `http://127.0.0.1:8001/v1/audio/speech` |
| `--instruction` | qwen3_local 音色描述 | 年轻专业男声，短视频解说... |
| `--voice` | edge 音色 | `zh-CN-YunyangNeural` |
| `--rate` | edge 语速 | `+15%` |
| `--speed` | qwen3_local 加速倍数（保调） | `1.25` |
| `--bgm-volume` | BGM 音量 0–1 | `0.18` |
| `--mapping` | 图文对应 JSON | 顺序轮播 |
| `--font` | 字体文件 | 自动查找 |
| `-o, --output` | 输出 mp4 | **必填** |

## 🎯 图文同步（mapping）

默认按文案段顺序轮播截图。要"说到导出按钮就显示按钮截图"，用 `--mapping`：

```json
[[6], [9], [6], [7], [8,9], [9], [10], [9], [9], [9], [1], [9]]
```

第 N 个列表 = 第 N 段文案用的截图索引（1-based；多张表示该段内快切）。

## 🤖 作为 Claude Skill 使用

本项目也提供 [SKILL.md](SKILL.md)，作为 Claude Code（或其他 AI agent）的 skill。安装后在对话里说"用 doc2video 把这个教程做成视频"，AI 会自动跑完整流程。

## 📄 License

MIT © CGIFM
