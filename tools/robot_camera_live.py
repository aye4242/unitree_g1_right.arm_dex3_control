#!/usr/bin/env python3
import argparse
import http.server
import os
import pathlib
import signal
import socketserver
import subprocess
import sys
import tempfile
import textwrap
import threading
import time


REMOTE_CAPTURE_CODE = r'''
import glob
import os
import sys
import time

import cv2

width = int(os.environ.get("CAMERA_WIDTH", "640"))
height = int(os.environ.get("CAMERA_HEIGHT", "480"))
fps = float(os.environ.get("CAMERA_FPS", "6"))
quality = int(os.environ.get("JPEG_QUALITY", "80"))
device = os.environ.get("VIDEO_DEVICE", "auto")

if device == "auto":
    candidates = []
    candidates += sorted(glob.glob("/dev/v4l/by-path/*1.3-video-index0"))
    candidates += sorted(glob.glob("/dev/v4l/by-path/*video-index0"))
    candidates += sorted(glob.glob("/dev/video*"))
else:
    candidates = [device]

seen = set()
candidates = [p for p in candidates if not (p in seen or seen.add(p))]

cap = None
opened_device = None
for candidate in candidates:
    test_cap = cv2.VideoCapture(candidate, cv2.CAP_V4L2)
    if not test_cap.isOpened():
        print(f"failed to open {candidate}", file=sys.stderr, flush=True)
        test_cap.release()
        continue

    test_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
    test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))
    test_cap.set(cv2.CAP_PROP_FPS, fps)
    test_cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
    ok, frame = test_cap.read()
    if ok and frame is not None:
        cap = test_cap
        opened_device = candidate
        break
    print(f"opened but failed to read {candidate}", file=sys.stderr, flush=True)
    test_cap.release()

if cap is None:
    print(
        "no readable video device; stop robot_snapshot.sh or other V4L2 users and retry",
        file=sys.stderr,
        flush=True,
    )
    sys.exit(2)

print(f"streaming {opened_device} {width}x{height}@{fps}", file=sys.stderr, flush=True)
delay = 1.0 / max(fps, 0.1)

try:
    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            time.sleep(0.05)
            continue
        ok, jpg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not ok:
            continue
        data = jpg.tobytes()
        sys.stdout.buffer.write(b"FRAME\n")
        sys.stdout.buffer.write(str(len(data)).encode("ascii") + b"\n")
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
        time.sleep(delay)
except BrokenPipeError:
    pass
finally:
    cap.release()
'''


INDEX_HTML = '''<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Robot Camera</title>
  <style>
    html, body { margin: 0; height: 100%; background: #111; color: #eee; font-family: sans-serif; }
    main { display: grid; min-height: 100%; place-items: center; }
    img { max-width: 100vw; max-height: 100vh; object-fit: contain; }
    .bar { position: fixed; left: 0; top: 0; right: 0; padding: 8px 10px; background: rgba(0,0,0,.65); font-size: 14px; }
  </style>
</head>
<body>
  <div class="bar">Robot camera live snapshot: <span id="stamp"></span></div>
  <main><img id="frame" src="latest.jpg"></main>
  <script>
    const img = document.getElementById('frame');
    const stamp = document.getElementById('stamp');
    setInterval(() => {
      const t = Date.now();
      img.src = 'latest.jpg?t=' + t;
      stamp.textContent = new Date(t).toLocaleTimeString();
    }, 250);
  </script>
</body>
</html>
'''


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return


def make_askpass(password):
    if not password:
        return None
    fd, path = tempfile.mkstemp(prefix="robot_camera_askpass_", text=True)
    with os.fdopen(fd, "w") as f:
        f.write("#!/bin/sh\n")
        f.write("printf '%s\\n' \"$ROBOT_PASSWORD\"\n")
    os.chmod(path, 0o700)
    return path


def start_http(directory, port):
    os.chdir(directory)
    server = socketserver.ThreadingTCPServer(("127.0.0.1", port), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def read_line(stream):
    line = stream.readline()
    if not line:
        raise EOFError("remote stream ended")
    return line.rstrip(b"\n")


def main():
    parser = argparse.ArgumentParser(description="Display the robot V4L2 camera through SSH.")
    parser.add_argument("--host", default=os.environ.get("ROBOT_HOST", "192.168.100.30"))
    parser.add_argument("--user", default=os.environ.get("ROBOT_USER", "unitree"))
    parser.add_argument("--password", default=os.environ.get("ROBOT_PASSWORD", "123"))
    parser.add_argument("--container", default=os.environ.get("CONTAINER_NAME", "unitree-dex3-dev"))
    parser.add_argument("--device", default=os.environ.get("VIDEO_DEVICE", "auto"))
    parser.add_argument("--fps", type=float, default=float(os.environ.get("CAMERA_FPS", "6")))
    parser.add_argument("--port", type=int, default=int(os.environ.get("CAMERA_VIEW_PORT", "8765")))
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()

    project_root = pathlib.Path(__file__).resolve().parents[1]
    out_dir = pathlib.Path(args.out_dir) if args.out_dir else project_root / "unitree_dex3" / "detect_img" / "live"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(INDEX_HTML, encoding="utf-8")

    askpass = make_askpass(args.password)
    env = os.environ.copy()
    if askpass:
        env.update({
            "ROBOT_PASSWORD": args.password,
            "SSH_ASKPASS": askpass,
            "SSH_ASKPASS_REQUIRE": "force",
            "DISPLAY": env.get("DISPLAY", ":0"),
        })
    env.update({
        "VIDEO_DEVICE": args.device,
        "CAMERA_FPS": str(args.fps),
    })

    remote_cmd = [
        "setsid", "ssh", "-o", "StrictHostKeyChecking=no",
        f"{args.user}@{args.host}",
        "docker", "exec", "-i",
        "-e", f"VIDEO_DEVICE={args.device}",
        "-e", f"CAMERA_FPS={args.fps}",
        args.container,
        "python3", "-u", "-",
    ]

    server = start_http(str(out_dir), args.port)
    print(f"Writing frames to: {out_dir / 'latest.jpg'}")
    print(f"Open in browser: http://127.0.0.1:{args.port}/")
    print("Press Ctrl+C to stop.")

    proc = subprocess.Popen(
        remote_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    assert proc.stdin is not None
    proc.stdin.write(REMOTE_CAPTURE_CODE.encode("utf-8"))
    proc.stdin.close()

    def stderr_reader():
        assert proc.stderr is not None
        for raw in proc.stderr:
            sys.stderr.write("[remote] " + raw.decode("utf-8", "replace"))

    threading.Thread(target=stderr_reader, daemon=True).start()

    latest = out_dir / "latest.jpg"
    tmp = out_dir / "latest.tmp"
    frames = 0
    started = time.time()
    try:
        assert proc.stdout is not None
        while True:
            marker = read_line(proc.stdout)
            if marker != b"FRAME":
                continue
            size = int(read_line(proc.stdout))
            data = proc.stdout.read(size)
            if len(data) != size:
                raise EOFError("incomplete frame")
            tmp.write_bytes(data)
            tmp.replace(latest)
            frames += 1
            if frames % max(1, int(args.fps * 5)) == 0:
                elapsed = max(0.1, time.time() - started)
                print(f"frames={frames} avg_fps={frames / elapsed:.1f}")
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
        if askpass:
            try:
                os.remove(askpass)
            except OSError:
                pass


if __name__ == "__main__":
    main()
