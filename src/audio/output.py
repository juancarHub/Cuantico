import os
import platform
import subprocess


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
        if self.backend in ("file", "windows", "playsound"):
            return True

        if self.backend in ("linux", "aplay", "sox"):
            return False

        return platform.system().lower().startswith("win")

    def play_file(self, path: str):
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
