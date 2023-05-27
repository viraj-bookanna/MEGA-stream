import requests,os
from flask import Flask, Response, request, stream_with_context, make_response
from mega import mega_file
from Crypto.Cipher import AES
from Crypto.Util import Counter

app = Flask(__name__)

@app.route('/download')
def download():
    if request.headers.get('Range', None) is not None:
        return make_response('Range Not Supported', 416)
    def stream_mega_file(file_info):
        counter = Counter.new(128, initial_value=int.from_bytes(file_info['iv'], byteorder='big'))
        cipher = AES.new(file_info['key'], AES.MODE_CTR, counter=counter)
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.93 Safari/537.36',
        }
        response = requests.get(file_info['url'], verify=False, headers=headers, stream=True)
        for chunk in response.iter_content(chunk_size=1024):
            yield cipher.decrypt(chunk)
    try:
        mega_url = request.args.get("url", None)
        if mega_url is None:
            with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'main.html'), 'r') as file:
                return Response(file.read(), content_type='text/html')
        file_info = mega_file(mega_url)
        if file_info['ok']:
            headers = {
                'Content-Type': 'application/octet-stream',
                'Content-Disposition': 'attachment; filename="{}"'.format(file_info['file_name']),
                'Content-Length': str(file_info['file_size']),
            }
            return Response(stream_with_context(stream_mega_file(file_info)), headers=headers)
        else:
            return Response(file_info['error'])
    except Exception as e:
        return Response(repr(e))

if __name__ == '__main__':
    app.run()