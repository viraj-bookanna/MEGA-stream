import aiohttp,os
from aiohttp import web
from mega import mega_file
from Crypto.Cipher import AES
from Crypto.Util import Counter


async def handler(request):
    async def stream_mega_file(file_info):
        first_chunk = True
        counter = Counter.new(128, initial_value=int.from_bytes(file_info['iv'], byteorder='big')+start_block_num)
        cipher = AES.new(file_info['key'], AES.MODE_CTR, counter=counter)
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(file_info['url'], headers=req_headers) as response:
                # Set the content type and headers for the response
                headers = {
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': 'attachment; filename="{}"'.format(file_info['file_name']),
                }
                if partial_content:
                    headers['Content-Length'] = int(response.headers.get('Content-Length'))-(start-actual_start)
                    headers['Content-Range'] = f"bytes {start}-{end}/{file_info['file_size']}"
                else:
                    headers['Content-Length'] = file_info['file_size']
                # Create a new aiohttp.web.StreamResponse object
                decrypted_response = web.StreamResponse(headers=headers)
                # Start the response
                await decrypted_response.prepare(request)
                # Stream and decrypt the chunks
                async for chunk in response.content.iter_chunked(1024):
                    # AES decryption
                    if first_chunk and partial_content:
                        decrypted_chunk = cipher.decrypt(chunk)[start-actual_start:]
                        first_chunk = False
                        await decrypted_response.write(decrypted_chunk)
                    else:
                        decrypted_chunk = cipher.decrypt(chunk)
                        await decrypted_response.write(decrypted_chunk)
                # Signal the end of the response
                await decrypted_response.write_eof()
                return decrypted_response
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
    try:
        mega_url = request.query.get("url", None)
        if mega_url is None:
            with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'main.html'), 'r') as file:
                return web.Response(text=file.read(), content_type='text/html')
        file_info = mega_file(mega_url)
        if file_info['ok']:
            return await stream_mega_file(file_info)
        else:
            return web.Response(text=file_info['error'])
    except Exception as e:
        return web.Response(text=repr(e))

# Create and run the aiohttp web server
app = web.Application()
app.router.add_get('/download', handler)
web.run_app(app)
