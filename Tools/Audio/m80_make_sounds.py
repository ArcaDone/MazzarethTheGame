"""Synthesised placeholder sounds for the GTA-like game (no sound assets in the project yet).

<python with numpy> Tools/Audio/m80_make_sounds.py Saved/Mazzarino80/Audio
(Blender's bundled Python has numpy: "C:/Program Files/Blender Foundation/Blender 4.3/4.3/python/bin/python.exe")
Writes 16-bit mono WAVs at 44.1 kHz:
  M80_Motore.wav      1 s seamless loop of a small two-cylinder engine at idle (pitch it up with the rpm)
  M80_Clacson.wav     80s Fiat horn (two close tones, a bit nasal)
  M80_Vetro.wav       a car window breaking
  M80_Esplosione.wav  a car blowing up
  M80_Lupara.wav      shotgun blast
  M80_Colpo.wav       a punch / blow landing
"""
import sys
import wave
from pathlib import Path

import numpy as np

SR = 44100
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
rng = np.random.default_rng(1980)


def save(name, x, gain=0.9):
    x = np.asarray(x, np.float64)
    x = x / max(1e-9, np.max(np.abs(x))) * gain
    data = (np.clip(x, -1, 1) * 32767).astype("<i2")
    OUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print("M80 wrote", OUT / name)


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def t_of(seconds):
    return np.arange(int(SR * seconds)) / SR


def engine():
    # Two cylinders at ~900 rpm: 15 firing pulses per second; harmonics of 1 Hz so the loop is seamless.
    t = t_of(1.0)
    fire = 15
    x = np.zeros_like(t)
    for h, a in ((1, 1.0), (2, 0.7), (3, 0.45), (4, 0.3), (6, 0.18), (8, 0.1)):
        x += a * np.sin(2 * np.pi * fire * h * t + h * 0.7)
    pulse = (0.5 + 0.5 * np.sin(2 * np.pi * fire * t)) ** 6
    noise = lowpass(rng.standard_normal(len(t)), 900)
    noise = noise - np.roll(noise, 1) * 0  # keep
    x = x * (0.55 + 0.45 * pulse) + 0.25 * noise * pulse
    x += 0.35 * np.sin(2 * np.pi * 30 * t)
    # Seamless: fade the noise part into its start.
    fade = int(0.02 * SR)
    x[-fade:] = x[-fade:] * np.linspace(1, 0, fade) + x[:fade] * np.linspace(0, 1, fade)
    save("M80_Motore.wav", lowpass(x, 2500), 0.8)


def horn():
    t = t_of(0.7)
    x = np.zeros_like(t)
    for f in (415.0, 495.0):
        ph = 2 * np.pi * f * t
        x += np.sign(np.sin(ph)) * 0.5 + 0.5 * np.sin(ph)
    env = np.minimum(1, t / 0.02) * np.minimum(1, (t[-1] - t) / 0.05)
    save("M80_Clacson.wav", lowpass(x * env, 3500), 0.7)


def glass():
    t = t_of(0.9)
    x = highpass(rng.standard_normal(len(t)), 2500) * np.exp(-t * 9)
    for _ in range(40):
        s = rng.uniform(0.02, 0.8)
        f = rng.uniform(2500, 7000)
        m = t >= s
        x[m] += 0.5 * np.sin(2 * np.pi * f * (t[m] - s)) * np.exp(-(t[m] - s) * rng.uniform(25, 60))
    save("M80_Vetro.wav", x, 0.8)


def explosion():
    t = t_of(2.8)
    n = rng.standard_normal(len(t))
    boom = lowpass(lowpass(n, 180), 180) * np.exp(-t * 1.6) * 6
    crack = highpass(n, 1500) * np.exp(-t * 18) * 0.6
    rumble = lowpass(n, 60) * np.exp(-t * 0.8) * 3
    save("M80_Esplosione.wav", boom + crack + rumble, 0.95)


def shotgun():
    t = t_of(0.9)
    n = rng.standard_normal(len(t))
    x = lowpass(n, 1200) * np.exp(-t * 9) * 2 + highpass(n, 3000) * np.exp(-t * 40) + lowpass(n, 120) * np.exp(-t * 4) * 2
    save("M80_Lupara.wav", x, 0.95)


def blow():
    t = t_of(0.25)
    n = rng.standard_normal(len(t))
    x = lowpass(n, 400) * np.exp(-t * 30) * 2 + np.sin(2 * np.pi * 90 * t) * np.exp(-t * 25)
    save("M80_Colpo.wav", x, 0.8)


for make in (engine, horn, glass, explosion, shotgun, blow):
    make()
