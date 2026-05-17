import os
import platform
import subprocess
import tempfile


class LinuxPipeline:
    def __init__(self, sox_proc, aplay_proc):
        self._sox = sox_proc
        self._aplay = aplay_proc
        self.stdin = sox_proc.stdin

    def wait(self):
        self._sox.wait()
        self._aplay.wait()


class AudioOutput:
    def __init__(self):
        self.backend = os.getenv("AUDIO_OUTPUT_BACKEND", "auto").lower()

    def use_file_backend(self):
        if self.backend in ("file", "windows", "winsound", "playsound"):
            return True

        if self.backend in ("linux", "aplay", "sox"):
            return False

        return platform.system().lower().startswith("win")

    def play_file(self, path: str):
        if self._should_use_winsound():
            self._play_file_windows_blocking(path)
            return

        self._play_file_playsound(path)

    def _should_use_winsound(self):
        if not platform.system().lower().startswith("win"):
            return False
        return self.backend in ("auto", "file", "windows", "winsound")

    def _play_file_windows_blocking(self, path: str):
        import winsound

        wav_path = self._convert_to_wav(path)
        try:
            winsound.PlaySound(wav_path, winsound.SND_FILENAME)
        finally:
            if wav_path != path:
                try:
                    os.remove(wav_path)
                except OSError:
                    pass

    def _convert_to_wav(self, path: str) -> str:
        lower = path.lower()
        if lower.endswith(".wav"):
            return path

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            wav_path = tmp.name

        try:
            from pydub import AudioSegment

            audio = AudioSegment.from_file(path)
            audio.export(wav_path, format="wav")
            return wav_path
        except Exception as exc:
            try:
                os.remove(wav_path)
            except OSError:
                pass
            raise RuntimeError(
                "No pude convertir el audio a WAV para reproducción bloqueante. "
                "Instala pydub y ffmpeg, o usa AUDIO_OUTPUT_BACKEND=playsound."
            ) from exc

    def _play_file_playsound(self, path: str):
        try:
            from playsound import playsound
        except Exception as exc:
            raise RuntimeError(
                "Falta playsound. Instala con: pip install playsound==1.2.2"
            ) from exc

        playsound(path)

    def create_linux_pipeline(self):
        sox_proc = subprocess.Popen(
            [
                "sox",
                "-q",
                "-t",
                "mp3",
                "-",
                "-t",
                "wav",
                "-",
                "highpass",
                "300",
                "bass",
                "-4",
                "treble",
                "+2",
                "gain",
                "-n",
                "-5",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        aplay_proc = subprocess.Popen(
            ["aplay", "-q", "-D", "default"],
            stdin=sox_proc.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        sox_proc.stdout.close()
        return LinuxPipeline(sox_proc, aplay_proc)
