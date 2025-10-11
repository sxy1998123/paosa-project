import os
import requests

def download_with_resume(url, filename, chunk_size=1024):
    # 已下载大小
    resume_byte_pos = 0
    if os.path.exists(filename):
        resume_byte_pos = os.path.getsize(filename)

    # 设置 Range 请求头
    headers = {}
    if resume_byte_pos > 0:
        headers['Range'] = f'bytes={resume_byte_pos}-'

    with requests.get(url, stream=True, headers=headers) as r:
        r.raise_for_status()

        # Content-Length 是剩余大小，如果有 Range 头的话
        total_size = int(r.headers.get('Content-Length', 0)) + resume_byte_pos  

        mode = 'ab' if resume_byte_pos > 0 else 'wb'

        downloaded = resume_byte_pos
        with open(filename, mode) as f:
            for chunk in r.iter_content(chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    print(f"\r已下载 {downloaded} / {total_size} 字节", end="")

    print("\n下载完成！")


if __name__ == "__main__":
    url = "http://localhost:5000/download/requirements.txt"
    download_with_resume(url, "largefile.zip")