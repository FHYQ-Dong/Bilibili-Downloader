import concurrent.futures
from tqdm import tqdm
import subprocess


class BLMerger():
    def __init__(self, ffmpeg_path=None):
        self.video_path = []
        self.audio_path = []
        self.output_path = []
        self.ffmpeg_path = ffmpeg_path if ffmpeg_path else "ffmpeg"
        
    def add(self, video_path, audio_path, output_path):
        if (type(video_path), type(audio_path), type(output_path)) == (str, str, str):
            self.video_path.append(video_path)
            self.audio_path.append(audio_path)
            self.output_path.append(output_path)
        elif (type(video_path), type(audio_path), type(output_path)) == (list, list, list):
            if len(video_path) == len(audio_path) == len(output_path):
                self.video_path.extend(video_path)
                self.audio_path.extend(audio_path)
                self.output_path.extend(output_path)
            else:
                raise ValueError("All input lists must have the same length.")
        else:
            raise ValueError("All inputs must be either lists or strings.")
        
    def run(self):
        if (type(self.video_path), type(self.audio_path), type(self.output_path)) == (list, list, list):
            if len(self.video_path) == len(self.audio_path) == len(self.output_path):
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = [executor.submit(self.merge, video, audio, output) for video, audio, output in zip(self.video_path, self.audio_path, self.output_path)]
                    p_bar = tqdm(total=len(futures), desc="Merging videos and audios")
                    for future in concurrent.futures.as_completed(futures):
                        p_bar.update(1)
                        p_bar.set_postfix_str(f"Completed: {future.result()}")
            else:
                raise ValueError("All input lists must have the same length.")
        elif (type(self.video_path), type(self.audio_path), type(self.output_path)) == (str, str, str):
            self.merge(self.video_path, self.audio_path, self.output_path)
        else:
            raise ValueError("All inputs must be either lists or strings.")
        
    def merge(self, video_path, audio_path, output_path):
        subprocess.Popen(
            [self.ffmpeg_path, "-i", video_path, "-i", audio_path, "-c:v", "copy", "-c:a", "copy", output_path, "-y"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        
if __name__ == "__main__":
    video_path = "downloads/video.mp4"
    audio_path = "downloads/audio.mp4"
    output_path = "downloads/output.mp4"
    
    # Example usage
    merger = BLMerger(video_path, audio_path, output_path)
    merger.run()