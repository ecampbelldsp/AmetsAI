import time
import torch
import numpy as np
from typing import Dict, Any, Tuple
from faster_whisper import WhisperModel


class STTEngine:
    """Loads and holds the heavy ML models in GPU memory."""

    def __init__(self, language="en", asr_model_size="base", device="cuda", compute_type="float16"):
        self.asr_model = WhisperModel(asr_model_size, device=device, compute_type=compute_type)
        self.vad_model, _ = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            trust_repo=True,
            verbose=False
        )
        self.vad_model.eval()
        self.language = language

    def create_session(self):
        return STTStreamSession(self.asr_model, self.vad_model, language = self.language)


class STTStreamSession:
    """Manages the audio buffer, VAD state machine, and precise metric extraction."""

    def __init__(self, asr_model, vad_model, language = "en", sample_rate=16000, window_size=512, silence_gap=0.8, vad_threshold=0.4):
        self.asr_model = asr_model
        self.vad_model = vad_model
        self.language = language

        self.sample_rate = sample_rate
        self.window_size = window_size
        self.silence_limit_chunks = int(silence_gap / (window_size / sample_rate))
        self.vad_threshold = vad_threshold

        self.reset_state()

    def reset_state(self):
        self.utterance_buffer = []
        self.continuous_silence_chunks = 0
        self.is_recording_utterance = False
        self.residual_samples = np.array([], dtype=np.float32)
        self.vad_model.reset_states()

    def process_chunk(self, raw_bytes: bytes, initial_prompt: str = None) -> Dict[str, Any] | None:
        new_samples = np.frombuffer(raw_bytes, dtype=np.float32)
        audio_stream = np.concatenate((self.residual_samples, new_samples))

        final_record = None

        while len(audio_stream) >= self.window_size:
            chunk = audio_stream[:self.window_size]
            audio_stream = audio_stream[self.window_size:]
            chunk_tensor = torch.from_numpy(chunk).float()

            with torch.no_grad():
                speech_prob = self.vad_model(chunk_tensor, self.sample_rate).item()

            if speech_prob > self.vad_threshold:
                self.is_recording_utterance = True
                self.continuous_silence_chunks = 0
                self.utterance_buffer.extend(chunk.tolist())

            elif self.is_recording_utterance:
                self.continuous_silence_chunks += 1
                self.utterance_buffer.extend(chunk.tolist())

                if self.continuous_silence_chunks >= self.silence_limit_chunks:
                    buffer_np = np.ascontiguousarray(np.array(self.utterance_buffer, dtype=np.float32))

                    # --- ALIGNED METRICS LOGIC ---
                    start_transcription = time.time()
                    segments, _ = self.asr_model.transcribe(
                        buffer_np, beam_size=1, language=self.language, word_timestamps=True, vad_filter=False, initial_prompt=initial_prompt
                    )
                    inference_time_s = time.time() - start_transcription
                    audio_duration_s = len(buffer_np) / self.sample_rate

                    full_text = ""
                    last_word_end_relative = 0.0
                    words_data = []

                    for segment in segments:
                        for word in segment.words:
                            full_text += word.word + " "
                            last_word_end_relative = word.end
                            words_data.append({
                                "word": word.word.strip(),
                                "start": word.start,
                                "end": word.end,
                                "confidence": word.probability
                            })

                    full_text = full_text.strip()

                    if full_text:
                        # Exact End-Point Latency Computation
                        endpoint_latency_s = (audio_duration_s + inference_time_s) - last_word_end_relative
                        rtf = inference_time_s / audio_duration_s if audio_duration_s > 0 else 0

                        final_record = {
                            "type": "transcript",
                            "text": full_text,
                            "metrics": {
                                "audio_duration_s": round(audio_duration_s, 2),
                                "inference_time_ms": round(inference_time_s * 1000, 0),
                                "rtf": round(rtf, 4),
                                "endpoint_latency_ms": round(endpoint_latency_s * 1000, 0)
                            },
                            "words_data": words_data
                        }

                    self.reset_state()

        self.residual_samples = audio_stream
        return final_record