#!/usr/bin/env python3
"""
doc2video — 把图文教程/截图 + 文案 → 推广短视频

输入：
  - 截图来源：图文教程 HTML（自动提取 base64 图片）或截图目录
  - 文案：txt（每行一段）
  - BGM：可选 mp3
  - TTS：qwen3_local（本地 8001 服务，音质好）/ edge_tts（免费，联网）

输出：mp4（截图轮播 + 配音 + 烧入字幕 + 可选 BGM）

示例：
  python make_promo_video.py \\
    --html 教程.html --script 文案.txt --bgm bgm.mp3 \\
    --tts qwen3_local -o out.mp4
"""
from __future__ import annotations
import argparse, base64, os, re, shutil, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ============ 工具函数 ============

def run(cmd, **kw):
    """跑命令，失败抛带 stderr 的异常"""
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"命令失败: {' '.join(cmd[:6])}...\n{r.stderr[-1500:]}")
    return r


def audio_duration(path: str) -> float:
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nw=1:nk=1", path]).stdout.strip()
    return float(out)


def find_font(font_arg: str | None) -> str:
    """查找可用中文字体"""
    if font_arg and Path(font_arg).is_file():
        return font_arg
    candidates = [
        # 项目自带
        Path(__file__).parent / "fonts" / "SourceHanSansCN-Regular.otf",
        # macOS
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        # Linux 常见
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return str(c)
    raise FileNotFoundError("找不到中文字体，请用 --font 指定 .otf/.ttc/.ttf")


# ============ 截图提取 ============

def extract_shots_from_html(html_path: str, out_dir: str) -> list[str]:
    """从 HTML 提取 base64 图片"""
    html = Path(html_path).read_text(encoding="utf-8", errors="ignore")
    imgs = re.findall(r"data:image/(jpeg|png);base64,([A-Za-z0-9+/=]+)", html)
    if not imgs:
        raise ValueError("HTML 里没找到 base64 图片")
    paths = []
    for i, (fmt, data) in enumerate(imgs, 1):
        ext = "jpg" if fmt == "jpeg" else "png"
        p = Path(out_dir) / f"{i:02d}.{ext}"
        p.write_bytes(base64.b64decode(data))
        paths.append(str(p))
    return paths


def load_shots(shots_dir: str) -> list[str]:
    """从目录读截图（按文件名排序）"""
    exts = (".jpg", ".jpeg", ".png", ".webp")
    files = [f for f in sorted(Path(shots_dir).iterdir()) if f.suffix.lower() in exts]
    return [str(f) for f in files]


def normalize_shots(shots: list[str], out_dir: str, size=(1920, 1080), bg="#f5f6f8") -> list[str]:
    """统一截图尺寸：缩放 contain + 居中贴到画布"""
    W, H = size
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for i, s in enumerate(shots, 1):
        im = Image.open(s).convert("RGB")
        im.thumbnail((W - 100, H - 120))
        canvas = Image.new("RGB", (W, H), bg)
        canvas.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
        p = d / f"{i:02d}.jpg"
        canvas.save(p, quality=88)
        out.append(str(p))
    return out


# ============ LLM 写文案 ============

def llm_write_script(shots, topic, llm_url, api_key, model, n_samples=3):
    """调视觉 LLM（默认 GLM-4V-Flash @ 8770）看截图 + 主题，生成短视频文案（每行一句）"""
    import requests, base64
    # 均匀采样 n_samples 张代表截图
    if len(shots) > n_samples:
        idx = [int(i * (len(shots) - 1) / (n_samples - 1)) for i in range(n_samples)]
        sample = [shots[i] for i in idx]
    else:
        sample = list(shots)
    prompt = (
        f"这是「{topic}」的视频截图（按时间顺序）。写一个 25-35 秒的短视频口播文案，硬性要求：\n"
        "- 一共 5-6 句，每句 15-25 字，总字数不超过 130 字\n"
        "- 第 1 句必须抓眼球（提问/反差/数字开头），禁止「大家好」「今天我们来聊聊」之类套话\n"
        "- 口语化、短句、快节奏，适合 1.25 倍速配音\n"
        "- 准确反映截图画面内容，紧扣主题\n"
        "- 只输出文案正文（每句一行），不要序号、不要解释、不要 markdown、不要结束语套话\n"
    )
    content = [{"type": "text", "text": prompt}]
    from io import BytesIO
    for s in sample:
        im = Image.open(s).convert("RGB")
        if max(im.size) > 1280:                        # 缩到最长边 1280，避免 base64 过大被拒
            im.thumbnail((1280, 1280))
        buf = BytesIO()
        im.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
    r = requests.post(f"{llm_url}/chat/completions",
                      json={"model": model, "messages": [{"role": "user", "content": content}], "temperature": 0.7},
                      headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                      timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"LLM 返回 {r.status_code}: {r.text[:400]}")
    text = r.json()["choices"][0]["message"]["content"]
    # 先按换行分
    lines = []
    for l in text.split("\n"):
        l = l.strip()
        if not l:
            continue
        l = re.sub(r"^[\d]+[.、)]\s*", "", l)      # 去序号
        l = re.sub(r"^[-•*]\s*", "", l)             # 去 bullet
        l = l.strip("`\"' ")
        if len(l) > 3:
            lines.append(l)
    # 若 LLM 没换行（写成整段），按句末标点断句
    if len(lines) <= 2:
        parts = re.split(r"(?<=[。！？\!\?])", text)
        lines = [p.strip().strip("`\"' ") for p in parts if len(p.strip()) > 4]
    if not lines:
        raise ValueError(f"LLM 没生成有效文案，原始返回：{text[:200]}")
    return lines


# ============ TTS ============

def tts_qwen3_local(text, api_url, instruction, out_wav, mode="design",
                    temperature=0.7, seed=42, max_tokens=4000):
    """调用本地 Qwen3-TTS MLX 服务（OpenAI 兼容 /v1/audio/speech）"""
    import requests
    payload = {"mode": mode, "text": text, "instruction": instruction,
               "temperature": temperature, "seed": seed, "max_tokens": max_tokens}
    r = requests.post(api_url, json=payload, timeout=200)
    r.raise_for_status()
    Path(out_wav).write_bytes(r.content)
    return r.headers.get("X-Generation-Seconds", "?")


def tts_edge(text, voice, rate, out_wav):
    """edge-tts 免费 TTS（联网）"""
    import asyncio, edge_tts
    async def _go():
        await edge_tts.Communicate(text, voice, rate=rate).save(out_wav)
    asyncio.run(_go())


def atempo_speed(src_wav, speed, out_wav):
    """ffmpeg atempo 加速（保持音调）；speed=1.0 时直��复制"""
    if abs(speed - 1.0) < 0.01:
        shutil.copy(src_wav, out_wav)
        return
    run(["ffmpeg", "-y", "-i", src_wav, "-filter:a", f"atempo={speed}", out_wav])


# ============ 字幕帧 ============

def make_frames(shots, lines, audio_dur, font_path, out_dir, mapping=None,
                size=(1920, 1080), font_size=46, bottom_margin=90, stroke=4):
    """生成图文同步的字幕帧 + concat list。
    mapping: 可选，list[list[int]]，每段对应截图索引(1-based)。None 时按顺序轮播。"""
    W, H = size
    n = len(shots)
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(font_path, font_size)
    totc = sum(len(l) for l in lines)
    frames = []; list_lines = []; t = 0.0; idx = 0
    for li, line in enumerate(lines):
        shot_indices = mapping[li] if (mapping and li < len(mapping)) else [(li % n) + 1]
        seg = audio_dur * len(line) / totc
        per = seg / len(shot_indices)
        for si in shot_indices:
            idx += 1
            sn = max(1, min(int(si), n))
            bg = Image.open(shots[sn - 1]).convert("RGB")
            draw = ImageDraw.Draw(bg)
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]; h = bbox[3] - bbox[1]
            x = (W - w) // 2; y = H - h - bottom_margin
            draw.text((x, y), line, font=font, fill="white",
                      stroke_width=stroke, stroke_fill="black")
            fp = d / f"{idx:02d}.jpg"
            bg.save(fp, quality=88)
            frames.append(str(fp))
            list_lines.append(f"file '{fp}'\nduration {per:.3f}\n")
            t += per
    list_lines.append(f"file '{frames[-1]}'\n")
    list_path = d / "concat.txt"
    list_path.write_text("".join(list_lines))
    return str(list_path)


# ============ 合成 ============

def compose(list_path, voice, bgm, output, bgm_volume=0.18, video_bitrate="4M"):
    """ffmpeg 合成最终视频：concat 图片 + 配音 +（可选）BGM ducking"""
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-i", voice]
    if bgm:
        cmd += ["-stream_loop", "-1", "-i", bgm,
                "-filter_complex",
                f"[1:a]volume=1.0[a1];[2:a]volume={bgm_volume}[a2];"
                f"[a1][a2]amix=inputs=2:duration=1:normalize=0[a]",
                "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "libx264", "-b:v", video_bitrate, "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", output]
    run(cmd)


# ============ 主流程 ============

def main():
    ap = argparse.ArgumentParser(description="doc2video - 图文教程/截图 → 推广短视频",
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_argument_group("输入素材")
    src.add_argument("--html", help="图文教程 HTML（自动提取 base64 截图）")
    src.add_argument("--shots", help="截图目录（与 --html 二选一）")
    src.add_argument("--script", help="文案 txt（每行一段，与 --topic 二选一）")
    src.add_argument("--topic", help="视频主题（不提供 --script 时，用 LLM 看截图自动写文案）")
    src.add_argument("--llm-url", default="http://127.0.0.1:8770/v1", help="视觉 LLM 端点（默认 glm-vision-proxy 8770）")
    src.add_argument("--llm-key", default="sk-glm-vision")
    src.add_argument("--llm-model", default="glm-4v-flash")
    src.add_argument("--bgm", help="背景音乐 mp3/m4a/wav")
    src.add_argument("--mapping", help="图文对应 JSON：[[1],[2,3],...] 每段对应截图索引")

    tts = ap.add_argument_group("TTS 配音")
    tts.add_argument("--tts", choices=["qwen3_local", "edge"], default="qwen3_local",
                     help="qwen3_local=本地8001服务(音质好,默认); edge=免费联网")
    tts.add_argument("--tts-url", default="http://127.0.0.1:8001/v1/audio/speech")
    tts.add_argument("--instruction", default="年轻专业男声，语速轻快有活力，短视频科技解说风格，咬字清晰")
    tts.add_argument("--voice", default="zh-CN-YunyangNeural", help="edge 音色")
    tts.add_argument("--rate", default="+15%", help="edge 语速")
    tts.add_argument("--speed", type=float, default=1.25, help="qwen3_local 加速倍数(保持音调)")

    out = ap.add_argument_group("输出/其他")
    out.add_argument("--bgm-volume", type=float, default=0.18, help="BGM 音量 0-1")
    out.add_argument("--voice-file", help="已有配音 wav/mp3（提供则跳过 TTS，用于外部生成的配音）")
    out.add_argument("--font", help="字幕字体 .otf/.ttc/.ttf")
    out.add_argument("--workdir", default="/tmp/doc2video_work")
    out.add_argument("-o", "--output", required=True, help="输出 mp4")
    args = ap.parse_args()

    if not args.html and not args.shots:
        sys.exit("❌ 需要 --html 或 --shots 提供截图来源")

    wd = Path(args.workdir); wd.mkdir(parents=True, exist_ok=True)
    shots_raw = wd / "shots_raw"; shots_norm = wd / "shots_norm"; frames = wd / "frames"
    for d in (shots_raw, shots_norm, frames):
        d.mkdir(exist_ok=True)

    # 1. 截图
    print("📸 [1/5] 准备截图...")
    if args.html:
        shots = extract_shots_from_html(args.html, shots_raw)
    else:
        shots = load_shots(args.shots)
    print(f"   提取 {len(shots)} 张截图")
    shots = normalize_shots(shots, shots_norm)

    # 2. 文案（--script 文件 或 --topic 用 LLM 生成）
    if args.script:
        lines = [l.strip() for l in Path(args.script).read_text(encoding="utf-8").splitlines() if l.strip()]
    elif args.topic:
        print(f"🤖 [1.5/5] LLM 看截图写文案 ({args.llm_model})...")
        lines = llm_write_script(shots, args.topic, args.llm_url, args.llm_key, args.llm_model)
        (wd / "script_auto.txt").write_text("\n".join(lines), encoding="utf-8")
        print(f"   自动文案已存: {wd / 'script_auto.txt'}")
    else:
        sys.exit("❌ 需要 --script（文案文件）或 --topic（主题，LLM 自动写文案）")
    text = "".join(lines)
    print(f"📝 [2/5] 文案 {len(text)} 字, {len(lines)} 段")

    # 3. TTS（或用已有配音）
    print(f"🔊 [3/5] 配音...")
    voice_raw = wd / "voice_raw.wav"; voice = wd / "voice.wav"
    if args.voice_file:
        print(f"   使用已有配音: {args.voice_file}")
        shutil.copy(args.voice_file, voice)
    elif args.tts == "qwen3_local":
        secs = tts_qwen3_local(text, args.tts_url, args.instruction, voice_raw)
        print(f"   qwen3_local 生成完成 (模型耗时 {secs}s)")
        atempo_speed(voice_raw, args.speed, voice)
    else:
        tts_edge(text, args.voice, args.rate, voice_raw)
        shutil.copy(voice_raw, voice)
    dur = audio_duration(str(voice))
    print(f"   配音时长 {dur:.1f}s")

    # 4. 字幕帧
    print("🖼️ [4/5] 生成字幕帧...")
    font_path = find_font(args.font)
    mapping = None
    if args.mapping:
        mapping = __import__("json").loads(Path(args.mapping).read_text())
    list_path = make_frames(shots, lines, dur, font_path, frames, mapping=mapping)

    # 5. 合成
    print(f"🎬 [5/5] 合成视频{' + BGM' if args.bgm else ''}...")
    compose(list_path, str(voice), args.bgm, args.output, args.bgm_volume)
    final_dur = audio_duration(args.output)
    print(f"✅ 完成: {args.output} ({final_dur:.1f}s)")


if __name__ == "__main__":
    main()
