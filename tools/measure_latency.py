#!/usr/bin/env python3
"""ACTG - Langkah 1: ukur latensi capture layar dan tap lewat adb (Termux).

Persiapan (sekali):
  pkg install python android-tools
  Developer options -> aktifkan Wireless debugging
  adb pair localhost:PORT_PAIR KODE
  adb connect localhost:PORT_CONNECT

Jalankan di HOME SCREEN (bukan di dalam game):
  python tools/measure_latency.py
  python tools/measure_latency.py --n 30 --x 5 --y 5
"""
import argparse
import statistics
import subprocess
import time


def adb_cmd(serial):
    return ["adb"] + (["-s", serial] if serial else [])


def stats(label, times_ms):
    print(
        f"{label:<34} rata2 {statistics.mean(times_ms):7.1f} ms | "
        f"min {min(times_ms):7.1f} | max {max(times_ms):7.1f}"
    )


def bench_capture(base, n, raw):
    cmd = base + ["exec-out", "screencap"] + ([] if raw else ["-p"])
    times, size = [], 0
    for _ in range(n):
        t = time.perf_counter()
        out = subprocess.run(cmd, capture_output=True).stdout
        times.append((time.perf_counter() - t) * 1000)
        size = len(out)
    stats(f"screencap {'RAW' if raw else 'PNG'} ({size // 1024} KB)", times)


def bench_tap_spawn(base, n, x, y):
    """Satu proses adb baru untuk tiap tap (lambat)."""
    cmd = base + ["shell", "input", "tap", str(x), str(y)]
    times = []
    for _ in range(n):
        t = time.perf_counter()
        subprocess.run(cmd, capture_output=True)
        times.append((time.perf_counter() - t) * 1000)
    stats("tap: adb baru tiap klik", times)


def bench_tap_persistent(base, n, x, y):
    """Satu shell adb yang tetap hidup, kirim perintah lewat stdin."""
    p = subprocess.Popen(
        base + ["shell"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    times = []
    for _ in range(n):
        t = time.perf_counter()
        p.stdin.write(f"input tap {x} {y}; echo __done__\n")
        p.stdin.flush()
        while "__done__" not in p.stdout.readline():
            pass
        times.append((time.perf_counter() - t) * 1000)
    p.stdin.write("exit\n")
    p.stdin.flush()
    p.wait(timeout=5)
    stats("tap: shell tetap hidup", times)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20, help="jumlah percobaan")
    ap.add_argument("--x", type=int, default=5, help="koordinat tap X (pojok, aman)")
    ap.add_argument("--y", type=int, default=5, help="koordinat tap Y")
    ap.add_argument("--serial", default=None, help="serial adb jika ada banyak device")
    a = ap.parse_args()

    base = adb_cmd(a.serial)
    devices = subprocess.run(base + ["devices"], capture_output=True, text=True).stdout
    print(devices.strip(), "\n")
    if "\tdevice" not in devices:
        raise SystemExit("Belum ada device. Jalankan adb pair / adb connect dulu.")

    print(f"Percobaan per tes: {a.n}\n")
    bench_capture(base, a.n, raw=False)
    bench_capture(base, a.n, raw=True)
    bench_tap_spawn(base, a.n, a.x, a.y)
    bench_tap_persistent(base, a.n, a.x, a.y)
    print("\nTarget ACTG: capture + tap total di bawah ~90 ms.")


if __name__ == "__main__":
    main()
