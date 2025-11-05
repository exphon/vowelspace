# test_parselmouth.py
import parselmouth
from parselmouth.praat import call
import sys

wav_path = sys.argv[1] if len(sys.argv) > 1 else "test/ftest_audio.wav"

snd = parselmouth.Sound(wav_path)
pitch = snd.to_pitch()
mean_f0 = call(pitch, "Get mean", 0, 0, "Hertz")
print(f"File: {wav_path}")
print("Mean F0 (Hz):", mean_f0)

# 예: 폼란트(F1,F2) 추출(시간 t에서 값 가져오기)
formant = snd.to_formant_burg()
t = snd.get_total_duration() / 2  # 중앙 시간
f1 = call(formant, "Get value at time", 1, t, "Hertz", "Linear")
f2 = call(formant, "Get value at time", 2, t, "Hertz", "Linear")
print("At time", round(t,3), "s -> F1:", f1, "Hz, F2:", f2, "Hz")