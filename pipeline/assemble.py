"""Stage 5: assembly with FFmpeg, driven by the storyboard timeline.

(default)    the film: shot clips in order + end card, narration, score ducked under the voice,
             burned-in English subtitles, loudness -16 LUFS. Exports
             outputs/final/film_9x16.mp4 (720x1280) and outputs/final/film_16x9.mp4 (1280x720, the vertical
             picture centred over a blurred, enlarged copy of itself).
             Music: outputs/music/chosen.wav if present, else the placeholder chord.

--radio-cut  narration + placeholder music (ducked under the voice) on a black screen, with English
             subtitles and the end card. The cheap prototype for user test 1.
             Writes outputs/radio_cut/radio_cut.mp4

Audio chain (shared with the final film): each narration clip delayed to its line start -> voice bus;
music ducked by a sidechain compressor keyed on the voice; mixed; loudness-normalised to -16 LUFS.
"""
import argparse
import json
import subprocess
import sys

from pipeline import subtitles
from pipeline.common.config import OUTPUTS, ROOT, load_storyboard

W, H, FPS = 720, 1280, 25


MUSIC = OUTPUTS / "music" / "chosen.wav"


def placeholder_music(total: float) -> str:
    """A soft, slow major chord with gentle movement: obviously temporary, not distracting."""
    expr = ("0.05*sin(2*PI*196*t)*(0.7+0.3*sin(2*PI*0.2*t))"
            "+0.035*sin(2*PI*246.94*t)*(0.7+0.3*sin(2*PI*0.27*t))"
            "+0.035*sin(2*PI*293.66*t)*(0.7+0.3*sin(2*PI*0.33*t))")
    return f"aevalsrc='{expr}':s=48000:d={total},afade=t=in:d=1.5,afade=t=out:st={total - 2}:d=2"


def audio_graph(tl: dict, first_input: int, music_input: int | None = None) -> tuple[list[str], str]:
    """Returns (filter lines, label of the final mixed audio). Narration clips are inputs first_input..;
    if music_input is given it is the score, otherwise a placeholder is synthesised."""
    lines, voice_labels = [], []
    clips = [s for s in tl["shots"] if "clip" in s]
    for i, s in enumerate(clips):
        ms = round(s["line_start"] * 1000)
        lines.append(f"[{first_input + i}:a]aresample=48000,aformat=channel_layouts=mono,adelay={ms}:all=1[v{i}]")
        voice_labels.append(f"[v{i}]")
    lines.append(f"{''.join(voice_labels)}amix=inputs={len(clips)}:normalize=0,apad=whole_dur={tl['total']}[voice]")
    lines.append("[voice]asplit=2[voice_out][voice_key]")
    if music_input is None:
        lines.append(f"{placeholder_music(tl['total'])}[music]")
    else:  # score: fit to the film, fade in and out, sit under the voice
        lines.append(f"[{music_input}:a]aresample=48000,aformat=channel_layouts=mono,volume=0.35,"
                     f"atrim=0:{tl['total']},apad=whole_dur={tl['total']},afade=t=in:d=1,"
                     f"afade=t=out:st={tl['total'] - 2.5}:d=2.5[music]")
    lines.append("[music][voice_key]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350:makeup=1[ducked]")
    lines.append("[voice_out][ducked]amix=inputs=2:normalize=0,"
                 "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,"
                 "aformat=channel_layouts=stereo[aout]")  # stereo: some players and platforms mishandle mono
    return lines, "[aout]"


def radio_cut() -> None:
    sb = load_storyboard()
    tl = subtitles.write(W, H)
    clips = [s for s in tl["shots"] if "clip" in s]
    missing = [s["id"] for s in tl["shots"] if "clip" not in s]
    if missing:
        print(f"warning: no narration for {', '.join(missing)} (run `python -m pipeline.narration`)", file=sys.stderr)

    out_dir = OUTPUTS / "radio_cut"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "radio_cut.mp4"
    ass = (OUTPUTS / "subtitles" / "film.ass").relative_to(ROOT)

    inputs = ["-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={FPS}:d={tl['total']}"]
    for s in clips:
        inputs += ["-i", s["clip"]]
    lines, aout = audio_graph(tl, first_input=1)
    lines.insert(0, f"[0:v]subtitles={ass}[vout]")

    cmd = ["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(lines),
           "-map", "[vout]", "-map", aout, "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-t", str(tl["total"]), "-movflags", "+faststart",
           str(out)]
    subprocess.run(cmd, check=True, cwd=ROOT)
    wav = out.with_suffix(".wav")  # audio-only copy: plays in any player, easy to send for user tests
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(out), "-vn", "-c:a", "pcm_s16le", str(wav)], check=True)
    print(f"radio cut: {out.relative_to(ROOT)} and {wav.name} ({tl['total']}s, {len(clips)} narration clips)")


def film() -> None:
    sb = load_storyboard()
    tl = subtitles.write(W, H)
    subtitles.write(H, W)
    shots_manifest = json.loads((OUTPUTS / "shots" / "manifest.json").read_text())
    missing = [s["id"] for s in tl["shots"] if s["id"] not in shots_manifest]
    if missing:
        sys.exit(f"missing shot clips for {', '.join(missing)}: run `python -m pipeline.shots`")
    clips = [s for s in tl["shots"] if "clip" in s]
    out_dir = OUTPUTS / "final"
    out_dir.mkdir(parents=True, exist_ok=True)

    # inputs: shot clips, end card (black), narration clips, optional music
    inputs, n = [], 0
    for s in tl["shots"]:
        inputs += ["-i", str(ROOT / shots_manifest[s["id"]]["file"])]
        n += 1
    card = tl["end_card"]
    inputs += ["-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={FPS}:d={card['dur']}"]
    n += 1
    first_voice = n
    for s in clips:
        inputs += ["-i", s["clip"]]
        n += 1
    music_input = None
    if MUSIC.exists():
        inputs += ["-i", str(MUSIC)]
        music_input = n
    lines = [f"{''.join(f'[{i}:v]' for i in range(first_voice))}concat=n={first_voice}:v=1:a=0,"
             f"settb=AVTB,fps={FPS}[base]", "[base]split=2[b916][b169]"]
    lines.append(f"[b916]subtitles={(OUTPUTS / 'subtitles' / 'film.ass').relative_to(ROOT)}[v916]")
    lines.append(f"[b169]split=2[bg][fg];[bg]scale={H}:{W}:force_original_aspect_ratio=increase,crop={H}:{W},"
                 f"boxblur=30:3,eq=brightness=-0.12[bgb];[fg]scale=-2:{W}[fgs];"
                 f"[bgb][fgs]overlay=(W-w)/2:0,"
                 f"subtitles={(OUTPUTS / 'subtitles' / f'film_{H}x{W}.ass').relative_to(ROOT)}[v169]")
    alines, aout = audio_graph(tl, first_voice, music_input)
    lines += alines + [f"{aout}asplit=2[a916][a169]"]
    enc = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-t", str(tl["total"]), "-movflags", "+faststart"]
    out916, out169 = out_dir / "film_9x16.mp4", out_dir / "film_16x9.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(lines),
           "-map", "[v916]", "-map", "[a916]", *enc, str(out916),
           "-map", "[v169]", "-map", "[a169]", *enc, str(out169)]
    subprocess.run(cmd, check=True, cwd=ROOT)
    methods = {}
    for m in shots_manifest.values():
        methods[m["method"]] = methods.get(m["method"], 0) + 1
    print(f"film: {out916.relative_to(ROOT)} and {out169.name} ({tl['total']}s; shots {methods}; "
          f"music {'chosen.wav' if music_input is not None else 'placeholder'})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--radio-cut", action="store_true")
    args = ap.parse_args()
    radio_cut() if args.radio_cut else film()


if __name__ == "__main__":
    main()
