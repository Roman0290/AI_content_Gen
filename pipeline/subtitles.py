"""English subtitles from the storyboard and narration timings.

Writes outputs/subtitles/film.en.srt  (for upload to platforms)
       outputs/subtitles/film.ass     (burned in by assembly: subtitles + end card, Noto Sans Ethiopic)
"""
from pipeline.common.config import OUTPUTS, load_storyboard
from pipeline.common.timeline import build

OUT = OUTPUTS / "subtitles"
MIN_ON_S, TAIL_S = 1.5, 0.4
FONT = "Noto Sans Ethiopic"  # covers Latin and Ge'ez, so the Amharic end card renders


def _srt_time(s: float) -> str:
    ms = round(s * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def _ass_time(s: float) -> str:
    cs = round(s * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02}:{cs // 100 % 60:02}.{cs % 100:02}"


def cues(tl: dict) -> list[tuple[float, float, str]]:
    out = []
    for s in tl["shots"]:
        start = s.get("line_start", s["start"])
        end = max(s.get("line_end", start) + TAIL_S, start + MIN_ON_S)
        out.append((start, min(end, s["start"] + s["dur"]), s["subtitle_en"]))
    return out


def write(width: int = 720, height: int = 1280) -> dict:
    sb = load_storyboard()
    tl = build(sb)
    OUT.mkdir(parents=True, exist_ok=True)
    cs = cues(tl)

    srt = "\n".join(f"{i}\n{_srt_time(a)} --> {_srt_time(b)}\n{t}\n" for i, (a, b, t) in enumerate(cs, 1))
    (OUT / "film.en.srt").write_text(srt, encoding="utf-8")

    sub_size, card_size = round(height * 0.034), round(height * 0.045)
    card = tl["end_card"]
    ass = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {width}", f"PlayResY: {height}", "WrapStyle: 0", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Alignment, "
        "MarginL, MarginR, MarginV, BorderStyle, Outline, Shadow",
        f"Style: Sub,{FONT},{sub_size},&H00FFFFFF,&H00000000,&H80000000,1,2,40,40,{round(height * 0.12)},1,3,0",
        f"Style: Card,{FONT},{card_size},&H00FFFFFF,&H00000000,&H00000000,1,5,40,40,0,1,0,0",
        "", "[Events]", "Format: Layer, Start, End, Style, Text",
    ]
    ass += [f"Dialogue: 0,{_ass_time(a)},{_ass_time(b)},Sub,{t}" for a, b, t in cs]
    ass.append(f"Dialogue: 0,{_ass_time(card['start'])},{_ass_time(card['start'] + card['dur'])},Card,"
               + card["text"].replace(" · ", "\\N"))
    name = "film.ass" if (width, height) == (720, 1280) else f"film_{width}x{height}.ass"
    (OUT / name).write_text("\n".join(ass) + "\n", encoding="utf-8")
    print(f"{len(cs)} subtitle cues, end card at {card['start']}s -> outputs/subtitles/{name}")
    return tl


if __name__ == "__main__":
    write()
    write(1280, 720)
