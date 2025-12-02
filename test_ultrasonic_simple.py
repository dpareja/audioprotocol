import numpy as np
import wave

# Test simple: generar y decodificar un tono ultrasónico
sample_rate = 44100
duration = 0.1  # 100ms
freq = 19000  # 19 kHz

# Generar tono
t = np.linspace(0, duration, int(sample_rate * duration), False)
tone = np.sin(2 * np.pi * freq * t)
tone = (tone * 32767 * 0.8).astype(np.int16)

# Guardar
with wave.open('test_tone.wav', 'w') as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(sample_rate)
    wav.writeframes(tone.tobytes())

print(f"✓ Tono generado: {freq} Hz, {duration}s")

# Leer y decodificar
with wave.open('test_tone.wav', 'r') as wav:
    frames = wav.readframes(wav.getnframes())
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0

# FFT
fft = np.fft.fft(audio)
freqs = np.fft.fftfreq(len(audio), 1/sample_rate)
positive_freqs = freqs[:len(freqs)//2]
positive_fft = np.abs(fft[:len(fft)//2])

# Encontrar pico
peak_idx = np.argmax(positive_fft)
detected_freq = positive_freqs[peak_idx]

print(f"✓ Frecuencia detectada: {detected_freq:.0f} Hz")
print(f"  Error: {abs(detected_freq - freq):.0f} Hz")

if abs(detected_freq - freq) < 100:
    print("✓ Detección exitosa!")
else:
    print("✗ Error en detección")
