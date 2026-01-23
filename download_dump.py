
import os
import sys
import requests
import time

def download_file(url, dest_folder):
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)

    local_filename = url.split('/')[-1]
    dest_path = os.path.join(dest_folder, local_filename)

    print(f"Downloading {url} to {dest_path}...")
    
    # Streaming, so we can iterate over the response.
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        total_length = r.headers.get('content-length')

        with open(dest_path, 'wb') as f:
            if total_length is None: # no content length header
                f.write(r.content)
            else:
                dl = 0
                total_length = int(total_length)
                start_time = time.time()
                for chunk in r.iter_content(chunk_size=8192): 
                    if chunk: 
                        dl += len(chunk)
                        f.write(chunk)
                        
                        # Progress bar
                        done = int(50 * dl / total_length)
                        percent = (dl / total_length) * 100
                        sys.stdout.write(f"\r[{'=' * done}{' ' * (50-done)}] {percent:.2f}%")
                        sys.stdout.flush()
    
    print(f"\nDownload complete: {dest_path}")
    return dest_path

if __name__ == "__main__":
    URL = "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"
    # Download to data directory relative to project root
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    
    download_file(URL, DATA_DIR)
