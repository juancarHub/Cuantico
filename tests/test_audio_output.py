from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from audio.output import AudioOutput


class AudioOutputTests(unittest.TestCase):
    def test_auto_backend_falls_back_to_playsound_without_ffmpeg(self):
        output = AudioOutput()
        output.backend = "auto"

        with patch.object(output, "_should_use_winsound", return_value=True), patch.object(
            output,
            "_play_file_windows_blocking",
            side_effect=RuntimeError("sin ffmpeg"),
        ), patch.object(output, "_play_file_playsound") as playsound:
            output.play_file("respuesta.mp3")

        playsound.assert_called_once_with("respuesta.mp3")

    def test_explicit_winsound_backend_reports_conversion_error(self):
        output = AudioOutput()
        output.backend = "winsound"

        with patch.object(output, "_should_use_winsound", return_value=True), patch.object(
            output,
            "_play_file_windows_blocking",
            side_effect=RuntimeError("sin ffmpeg"),
        ), self.assertRaises(RuntimeError):
            output.play_file("respuesta.mp3")

    def test_windows_backend_also_falls_back_to_playsound(self):
        output = AudioOutput()
        output.backend = "windows"

        with patch.object(output, "_should_use_winsound", return_value=True), patch.object(
            output,
            "_play_file_windows_blocking",
            side_effect=RuntimeError("sin ffmpeg"),
        ), patch.object(output, "_play_file_playsound") as playsound:
            output.play_file("respuesta.mp3")

        playsound.assert_called_once_with("respuesta.mp3")


if __name__ == "__main__":
    unittest.main()
