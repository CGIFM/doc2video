---
name: doc2video
description: 把图文教程/截图 + 文案生成推广短视频（TTS 配音 + 字幕 + BGM）。当用户要把 HTML 教程、产品文档、截图集合转成带解说的演示短视频时使用。适合做浏览器扩展、SaaS 工具、开源项目的推广物料。
---

# doc2video

把图文素材 + 文案 → 推广短视频（mp4）。

## 项目位置

`~/Projects/doc2video/`

主脚本：`make_promo_video.py`

## 何时触发

用户说类似这些时：
- "把这个使用教程 HTML 做成视频"
- "给这个扩展/工具做个介绍短视频"
- "用 doc2video 生成推广视频"
- "把这些截图和文案做成演示视频"

## 前置依赖

- **Python 3.10+** + `pip install -r ~/Projects/doc2video/requirements.txt`
- **ffmpeg**（系统）
- **字体**：macOS 自带；或 `--font` 指定
- **TTS**：
  - `qwen3_local`（默认）：需本地 8001 服务（Qwen3-TTS MLX，OpenAI 兼容 /v1/audio/speech）。音质好。
  - `edge_tts`：免费联网，开箱即用（`--tts edge`）。无本地服务时用它。

## 执行流程

1. **收集素材**（缺一不可，缺了向用户要）：
   - 截图来源：HTML 文件（含 base64 图）**或** 截图目录
   - 文案 txt：每行一段。用户没给就根据教程内容自己写（短视频风格，每段 15-25 字）
   - BGM（可选）：问用户有没有 mp3，没有就跳过

2. **可选：图文对应**
   - 默认按顺序轮播，但常图文不同步
   - 提升质量：分析每张截图内容，给每段文案配最贴切的截图索引，写成 mapping JSON

3. **运行脚本**：
   ```bash
   cd ~/Projects/doc2video
   python make_promo_video.py \
     --html <教程.html>  \
     --script <文案.txt> \
     [--bgm <bgm.mp3>] \
     [--tts qwen3_local|edge] \
     [--mapping <mapping.json>] \
     -o <输出.mp4>
   ```

4. **交付**：把 mp4 路径告诉用户，`open` 打开预览。

## 常用参数速查

| 参数 | 默认 | 说明 |
|------|------|------|
| `--html` / `--shots` | - | 截图来源（二选一） |
| `--script` | 必填 | 文案 txt |
| `--bgm` | - | 背景音乐 |
| `--tts` | `qwen3_local` | `qwen3_local` / `edge` |
| `--instruction` | 年轻专业男声... | qwen3_local 音色描述 |
| `--voice` | `zh-CN-YunyangNeural` | edge 音色 |
| `--speed` | `1.25` | qwen3_local 加速倍数（保调） |
| `--rate` | `+15%` | edge 语速 |
| `--bgm-volume` | `0.18` | BGM 音量 |
| `--mapping` | 顺序轮播 | 图文对应 JSON |

## 注意事项

- **本地 8001 服务**：用 qwen3_local 时确认在跑（curl 8001/health）。没跑就 fallback 到 `--tts edge`。
- **ffmpeg subtitles filter 可能没编译 libass**：本脚本用 PIL 把字幕直接画到帧上，不依赖 ffmpeg subtitles filter，所以 brew ffmpeg 也能用。
- **字体读不了 ttc**：PingFang.ttc 在某些 PIL 版本打不开，脚本会自动 fallback 找其他字体；不行就 `--font` 指定 otf。
- **图文同步很重要**：用户最常反馈的问题是"画面跟不上解说"。尽量用 `--mapping` 精准对应。

## 典型对���

> 用户：用 doc2video 把这个 `使用教程.html` 做成 30 秒推广视频

AI 动作：
1. 读 HTML，提取截图，看每张是什么步骤
2. 根据教程 + 用户口述要点，写短视频文案（12 段左右，存 txt）
3. 分析截图-文案对应，写 mapping.json
4. 问用户有没有 BGM（或用默认无）
5. 跑 `make_promo_video.py`，交付 mp4
6. 让用户预览，根据反馈调（语速/BGM 音量/图文对应）

## 关联

完整文档见项目根的 `README.md` 和 `docs/USAGE.md`。
