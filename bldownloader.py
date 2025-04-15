import requests
import pathvalidate
import concurrent.futures
import json
import os
import time
from urllib.parse import urlparse
from tqdm import tqdm
import threading
from blauth import BLAuth
from lxml import etree
from blmerge import BLMerger


class MultiThreadDownloader:
    def __init__(self, max_workers=5, chunk_size=1024*1024, timeout=30, retry=3, headers=None):
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.timeout = timeout
        self.retry = retry
        self.session = requests.Session()
        if headers != None:
            self.session.headers.update(headers)
        else:
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
                'referer': 'https://www.bilibili.com'
            })
        self._lock = threading.Lock()
    
    def download_file(self, url, save_path=None, file_name=None, use_segments=True, segment_size=10*1024*1024):
        if save_path is None:
            save_path = os.getcwd()
        
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        
        # 确定文件名
        if file_name is None:
            file_name = os.path.basename(urlparse(url).path)
            if not file_name:
                file_name = f"download_{int(time.time())}"
        
        file_path = os.path.join(save_path, file_name)
        
        # 检查是否支持断点续传
        try:
            response = self.session.head(url, timeout=self.timeout)
            total_size = int(response.headers.get('content-length', 0))
            support_range = 'accept-ranges' in response.headers and response.headers['accept-ranges'] == 'bytes'
        except Exception as e:
            print(f"获取文件信息失败: {e}")
            total_size = 0
            support_range = False
        
        # 如果文件太小或不支持断点续传，直接下载
        if not support_range or total_size < segment_size or not use_segments:
            return self._direct_download(url, file_path)
        
        # 分段下载
        return self._segmented_download(url, file_path, total_size, segment_size)
    
    def _direct_download(self, url, file_path):
        for attempt in range(self.retry + 1):
            try:
                with self.session.get(url, stream=True, timeout=self.timeout) as response:
                    response.raise_for_status()
                    total_size = int(response.headers.get('content-length', 0))
                    
                    with open(file_path, 'wb') as f, tqdm(
                            desc=os.path.basename(file_path)[0:20],
                            total=total_size,
                            unit='B',
                            unit_scale=True,
                            unit_divisor=1024,
                        ) as bar:
                        for chunk in response.iter_content(chunk_size=self.chunk_size):
                            if chunk:
                                f.write(chunk)
                                bar.update(len(chunk))
                return file_path
            except Exception as e:
                if attempt < self.retry:
                    print(f"下载失败，尝试重试 ({attempt+1}/{self.retry}): {e}")
                    time.sleep(1)
                else:
                    print(f"下载失败: {url}, 错误: {e}")
                    return None
    
    def _download_segment(self, url, file_path, start, end, position, pbar):
        temp_file = f"{file_path}.part{position}"
        headers = {'Range': f'bytes={start}-{end}'}
        
        for attempt in range(self.retry + 1):
            try:
                with self.session.get(url, headers=headers, stream=True, timeout=self.timeout) as response:
                    response.raise_for_status()
                    with open(temp_file, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=self.chunk_size):
                            if chunk:
                                f.write(chunk)
                                with self._lock:
                                    pbar.update(len(chunk))
                return True, position
            except Exception as e:
                if attempt < self.retry:
                    print(f"分段 {position} 下载失败，尝试重试 ({attempt+1}/{self.retry}): {e}")
                    time.sleep(1)
                else:
                    print(f"分段 {position} 下载失败: {e}")
                    return False, position
    
    def _segmented_download(self, url, file_path, total_size, segment_size):
        """分段下载文件"""
        segments = []
        for i in range(0, total_size, segment_size):
            start = i
            end = min(i + segment_size - 1, total_size - 1)
            segments.append((start, end, len(segments)))
        
        with tqdm(desc=os.path.basename(file_path)[0:20], total=total_size, unit='B', unit_scale=True, unit_divisor=1024) as pbar:
            # 创建线程池下载各个分段
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for start, end, position in segments:
                    future = executor.submit(
                        self._download_segment, url, file_path, start, end, position, pbar
                    )
                    futures.append(future)
                
                # 等待所有任务完成
                results = [future.result() for future in futures]
                
                # 检查是否所有分段都成功下载
                if not all(success for success, _ in results):
                    print("部分分段下载失败，无法合并文件")
                    return None
        
        # 合并文件分段
        with open(file_path, 'wb') as outfile:
            for i in range(len(segments)):
                temp_file = f"{file_path}.part{i}"
                with open(temp_file, 'rb') as infile:
                    outfile.write(infile.read())
                os.remove(temp_file)
        
        print(f"文件下载完成: {file_path}")
        return file_path
    
    def download_files(self, urls, save_path=None, file_names=None, use_segments=False, segment_size=10*1024*1024):
        if file_names != None:
            if len(urls) != len(file_names):
                raise ValueError("URLs and file names must have the same length.")
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(self.download_file, url, save_path, file_name, use_segments, segment_size) for url, file_name in zip(urls, file_names)]
                p_bar = tqdm(total=len(futures), desc="Downloading files")
                for future in concurrent.futures.as_completed(futures):
                    p_bar.update(1)
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(self.download_file, url, save_path, use_segments=use_segments, segment_size=segment_size) for url in urls]
                p_bar = tqdm(total=len(futures), desc="Downloading files")
                for future in concurrent.futures.as_completed(futures):
                    p_bar.update(1)
        p_bar.close()


class BLDownloader(BLAuth, MultiThreadDownloader):
    def __init__(self, max_workers=5, chunk_size=1024*1024, timeout=30, retry=3, headers=None, ffmpeg_path=None):
        MultiThreadDownloader.__init__(self, max_workers, chunk_size, timeout, retry, headers)
        BLAuth.__init__(self)
        self.merger = BLMerger(ffmpeg_path)
        
    def _get_detail_av_url(self, title, bvid, pid, retry=3):
        url = self.VIDEO_URL.format(bvid, pid)
        for attempt in range(retry + 1):
            try:
                resp = self.get(url)
                resp.encoding = 'utf-8'
                html = etree.HTML(resp.text)
                with open('html.html', 'w', encoding='utf-8') as f:
                    f.write(resp.text)
                avurls = [s for s in html.xpath('//head[@itemprop="video"]/script/text()') if 'window.__playinfo__' in s][0].replace('window.__playinfo__=','')
                avurls = json.loads(avurls)
                video_url = avurls['data']['dash']['video'][0]['baseUrl']
                audio_url = avurls['data']['dash']['audio'][0]['baseUrl']
                return title, video_url, audio_url
            except Exception as e:
                if attempt < retry:
                    self.logger.warning(f"Fetching video data failed, retrying ({attempt+1}/{retry}): {e}")
                    time.sleep(1)
                else:
                    self.logger.error(f"Fetching video data failed {title}: {e}")
                    return title, None, None
    
    def _get_bvid_data(self, bvid):
        try:
            resp = self.get(self.CID_URL.format(bvid))
            resp.encoding = 'utf-8'
            episodes = { ep['part']: {
                "title": ep['part'],
                "pid": pid + 1,
                "bvid": bvid,
            } for pid, ep in enumerate(resp.json()['data']) }
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(self._get_detail_av_url, ep['title'], bvid, ep['pid']) for ep in episodes.values()]
                p_bar = tqdm(total=len(futures), desc="Fetching video data")
                for future in concurrent.futures.as_completed(futures):
                    p_bar.update(1)
                    title, video_url, audio_url = future.result()
                    if video_url and audio_url:
                        episodes[title]['video_url'] = video_url
                        episodes[title]['audio_url'] = audio_url
                    else:
                        self.logger.error(f"Failed to fetch video/audio URL for {title}")
            p_bar.close()
            return episodes
        except Exception as e:
            self.logger.error(f"Fetching bvid data failed: {e}")
            return None

    def _check_cache(self, save_path, file_name):
        if os.path.exists(os.path.join(save_path, file_name)):
            return True
        return False

    def download_bvid(self, bvid, save_path=None, use_segments=False, segment_size=10*1024*1024, cache=True):
        if not bvid:
            self.logger.error("BVID is required.")
            return
        if save_path is None:
            save_path = os.path.join(os.getcwd(), 'data', 'downloads', bvid)
        if not os.path.exists(save_path):
            os.makedirs(save_path)
            
        episodes = self._get_bvid_data(bvid)
        if not episodes:
            self.logger.error("No episodes found.")
            return
        
        for ep in episodes.values():
            title = ep['title']
            video_url = ep['video_url']
            audio_url = ep['audio_url']
            video_file = f"{pathvalidate.sanitize_filename(title, '_')}_video.mp4"
            audio_file = f"{pathvalidate.sanitize_filename(title, '_')}_audio.mp4"
            final_file = f"{pathvalidate.sanitize_filename(title, '_')}.mp4"
            if cache and ((self._check_cache(save_path, video_file) and self._check_cache(save_path, audio_file)) or self._check_cache(save_path, final_file)):
                self.logger.info(f"File already exists: {video_file} and {audio_file}, skipping download.")
                continue
            if not video_url or not audio_url:
                self.logger.error(f"Missing video/audio URL for {title}, skipping download.")
                continue
            self.download_files(
                urls=[video_url, audio_url],
                save_path=save_path,
                file_names=[video_file, audio_file],
                use_segments=use_segments,
                segment_size=segment_size
            )
        
        self.merger.add(
            video_path=[os.path.join(save_path, f"{pathvalidate.sanitize_filename(ep['title'], '_')}_video.mp4") for ep in episodes.values()],
            audio_path=[os.path.join(save_path, f"{pathvalidate.sanitize_filename(ep['title'], '_')}_audio.mp4") for ep in episodes.values()],
            output_path=[os.path.join(save_path, f"{pathvalidate.sanitize_filename(ep['title'], '_')}.mp4") for ep in episodes.values()],
        )
        self.merger.run()
        
        for ep in episodes.values():
            os.remove(os.path.join(save_path, f"{pathvalidate.sanitize_filename(ep['title'], '_')}_video.mp4"))
            os.remove(os.path.join(save_path, f"{pathvalidate.sanitize_filename(ep['title'], '_')}_audio.mp4"))
            

def main():
    downloader = BLDownloader(max_workers=4)
    downloader.login()
    downloader.download_bvid('BV19odKYWEcw')


if __name__ == "__main__":
    main()