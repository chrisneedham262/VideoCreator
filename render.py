# render.py
import json, subprocess, shlex, tempfile, os, sys

def run(cmd):
    print("→", cmd)
    subprocess.check_call(shlex.split(cmd))

def main(template_path, var_mapping):
    with open(template_path) as f:
        tpl = f.read()
    for k, v in var_mapping.items():
        tpl = tpl.replace("{{" + k + "}}", v)
    spec = json.loads(tpl)

    w, h, fps = spec["raster"]["w"], spec["raster"]["h"], spec["raster"]["fps"]
    crf = spec["output"]["crf"]; preset = spec["output"]["preset"]; ab = spec["output"]["audio_bitrate"]

    # Collect inputs
    inputs = []
    vid_labels = {}
    for v in spec["tracks"]["video"]:
        inputs.append(v["src"])
        vid_labels[v["id"]] = len(inputs)-1

    gfx_inputs = []
    for g in spec["tracks"]["graphics"]:
        gfx_inputs.append(g["src"])

    audio_inputs = [a["src"] for a in spec["tracks"]["audio"]]
    caps = spec["tracks"].get("captions")

    # Pre-normalize music (optional but consistent)
    music_src = [a for a in spec["tracks"]["audio"] if a.get("id") == "music"][0]["src"]
    music_norm = os.path.join(tempfile.gettempdir(), "music_norm.wav")
    run(f'ffmpeg -y -i "{music_src}" -af "loudnorm=I=-14:LRA=11:TP=-1.5" "{music_norm}"')

    # Build ffmpeg args
    all_inputs = []
    for p in inputs: all_inputs += ["-i", p]
    for p in gfx_inputs: all_inputs += ["-i", p]
    vo_src = [a for a in spec["tracks"]["audio"] if a.get("id") == "vo"][0]["src"]
    all_inputs += ["-i", vo_src, "-i", music_norm]

    # Index helpers
    V = range(len(inputs))
    G = range(len(inputs), len(inputs)+len(gfx_inputs))
    VO = len(inputs)+len(gfx_inputs)      # voiceover index
    MU = VO+1                              # music index

    fc = []  # filter_complex lines

    # Normalize, scale and time each base video
    for i, vitem in enumerate(spec["tracks"]["video"]):
        fc.append(f'[{i}:v]scale={w}:{h},fps={fps},format=yuv420p,setsar=1,'
                  f'trim=start={vitem["in"]}:end={vitem["out"]},setpts=PTS-STARTPTS[v{i}]')

    # Crossfade (simple pair-wise based on "transitions")
    out_chain = f'[v0]'
    for tr in spec["transitions"]:
        a = vid_labels[tr["between"][0]]
        b = vid_labels[tr["between"][1]]
        dur = tr["duration"]
        # ensure both streams exist as [v{a}] and [v{b}]
        fc.append(f'[v{a}][v{b}]xfade=transition=fade:duration={dur}:offset=4.0[vx{b}]')
        out_chain = f'[vx{b}]'  # crude: assumes sequential

    # Overlay graphics with enable windows
    last = out_chain
    base = last
    for gi, g in enumerate(spec["tracks"]["graphics"]):
        enable = f"enable='between(t,{g['at']},{g['at']+g['duration']})'"
        x = g["x"]; y = g["y"]
        fc.append(f'{base}[{len(inputs)+gi}:v]overlay=x={x}:y={y}:{enable}[vg{gi}]')
        base = f'[vg{gi}]'
    vout = base

    # Audio: sidechain duck music under VO
    fc.append(f'[{MU}:a][{VO}:a]sidechaincompress=threshold=0.05:ratio=8:attack=5:release=100[amix]')
    aout = '[amix]'

    # Subtitles (soft by default)
    maps = ['-map', vout, '-map', aout]
    sub_args = []
    if caps and caps["src"] and not caps.get("burn_in", False):
        sub_args = ['-i', caps["src"], '-c:s', 'mov_text', '-map', f'{len(all_inputs)}:s?']  # soft subs

    # Final command
    out_mp4 = os.path.join("output", "video.mp4")
    os.makedirs("output", exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        *all_inputs,
        *sub_args,
        "-filter_complex", "; ".join(fc),
        *maps,
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-c:a", "aac", "-b:a", ab,
        "-movflags", "+faststart",
        out_mp4
    ]
    run(" ".join(shlex.quote(x) for x in cmd))
    print("Done →", out_mp4)

if __name__ == "__main__":
    # Example variables you change per video:
    vars_example = {
        "INTRO_MP4": "assets/aroll/intro.mp4",
        "A_ROLL1": "assets/aroll/host_clip1.mp4",
        "B_ROLL1": "assets/broll/city_01.mp4",
        "TITLE_PNG": "assets/gfx/title.png",
        "LOWER_THIRD_PNG": "assets/gfx/lowerthird.png",
        "VOICEOVER_WAV": "assets/audio/vo.wav",
        "MUSIC_MP3": "assets/audio/bed.mp3",
        "CAPTIONS_SRT": "assets/captions/subs.srt"
    }
    template = sys.argv[1] if len(sys.argv) > 1 else "template.json"
    main(template, vars_example)
