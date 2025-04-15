from bldownloader import BLDownloader
import argparse, os

def parse_args():
    DOWNLOAD_PATH = r"data/downloads"
    parser = argparse.ArgumentParser(description="Download and merge videos and audios.")
    parser.add_argument("--bvid", "-b", type=str, default=None, help="BVID of the video.")
    parser.add_argument("--use_segments", "-s", action="store_true", default=True, help="Use segmented download.")
    parser.add_argument("--segment_size", "-ss", type=int, default=25*1024*1024, help="Segment size in bytes.")
    parser.add_argument("--ffmpeg_path", "-f", type=str, default=None, help="Path to ffmpeg executable.")
    parser.add_argument("--max_workers", "-w", type=int, default=8, help="Number of concurrent workers.")
    parser.add_argument("--timeout", "-t", type=int, default=30, help="Timeout for each download in seconds.")
    parser.add_argument("--retry", "-r", type=int, default=3, help="Number of retries for each download.")
    parser.add_argument("--download_path", "-d", type=str, default=DOWNLOAD_PATH, help="Path to save downloaded files.")
    parser.add_argument("--cache", "-c", action="store_true", default=True, help="Use cached files if available.")
    return parser.parse_args()

def main():
    args = parse_args()
    
    downloader = BLDownloader(
        max_workers=args.max_workers,
        chunk_size=args.segment_size,
        timeout=args.timeout,
        retry=args.retry,
        ffmpeg_path=args.ffmpeg_path,
    )
    downloader.login()
    downloader.download_bvid(
        args.bvid,
        save_path=args.download_path,
        use_segments=args.use_segments,
        cache=args.cache,
    )


if __name__ == "__main__":
    main()
    