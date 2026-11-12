import os
import subprocess
import shutil

class VideoExportMixin:
    def convert_instagram(self, source, destination):
        #ffmpeg = shutil.which("ffmpeg")
        ffmpeg = shutil.which("ffmpeg")

        if ffmpeg is None and os.path.isfile("/opt/homebrew/bin/ffmpeg"):
            ffmpeg = "/opt/homebrew/bin/ffmpeg"

        if ffmpeg is None:
            raise RuntimeError(
                "FFmpegが見つかりません。"
                "FFmpegをインストールしてPATHに登録してください。"
        )

        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", source,

            # 元画像の縦横比を保持
            "-vf",
            (
                "scale=1080:1920:"
                "force_original_aspect_ratio=decrease:"
                "force_divisible_by=2,"
                "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
                "setsar=1"
            ),

            "-r", "30",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-an",
            destination
        ]

        kwargs = {}

        if os.name == "nt":
            kwargs["creationflags"] = (
                subprocess.CREATE_NO_WINDOW
            )

        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            **kwargs
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Instagram変換エラー:\n"
                + result.stderr[-1500:]
            )

