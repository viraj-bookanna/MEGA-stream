import requests,os,re
from flask import Flask, Response, request, stream_with_context, make_response
from mega import mega_file
from Crypto.Cipher import AES
from Crypto.Util import Counter

app = Flask(__name__)

@app.route('/download')
def download():
    if request.headers.get('Range', None) is not None:
        m_range = re.search('^bytes=(\d+)-(\d+)?$', request.headers.get('Range', None))
        if m_range is None:
            return make_response('Range Not Supported', 416)
        partial_content = True
        start = int(m_range[1])
        end = '' if m_range[2] is None else int(m_range[2])
        start_block_num = start // 16
        actual_start = start_block_num * 16
        req_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.93 Safari/537.36',
            'Range': f'bytes={actual_start}-{end}',
        }
    else:
        partial_content = False
        start_block_num = 0
        req_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.93 Safari/537.36',
        }
    def stream_mega_file(file_info, response):
        first_chunk = True
        counter = Counter.new(128, initial_value=int.from_bytes(file_info['iv'], byteorder='big')+start_block_num)
        cipher = AES.new(file_info['key'], AES.MODE_CTR, counter=counter)
        for chunk in response.iter_content(chunk_size=1024):
            if first_chunk and partial_content:
                dec = cipher.decrypt(chunk)
                first_chunk = False
                yield dec[start-actual_start:]
            else:
                yield cipher.decrypt(chunk)
    #try:
    mega_url = request.args.get("url", None)
    if mega_url is None:
        with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'main.html'), 'r') as file:
            return Response(file.read(), content_type='text/html')
    file_info = mega_file(mega_url)
    if file_info['ok']:
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(file_info['url'], verify=False, headers=req_headers, stream=True)
        headers = {
            'Content-Type': 'application/octet-stream',
            'Content-Disposition': 'attachment; filename="{}"'.format(file_info['file_name']),
        }
        if partial_content:
            headers['Content-Length'] = int(response.headers.get('Content-Length'))-(start-actual_start)
            headers['Content-Range'] = f"bytes {start}-{end}/{file_info['file_size']}"
        else:
            headers['Content-Length'] = file_info['file_size']
        return Response(stream_with_context(stream_mega_file(file_info, response)), response.status_code, headers=headers)
    else:
        return Response(file_info['error'])
    #except Exception as e:
        #return Response(repr(e))

if __name__ == '__main__':
    app.run()