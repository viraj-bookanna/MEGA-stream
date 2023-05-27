import aiohttp,os
from aiohttp import web
from mega import mega_file
from Crypto.Cipher import AES
from Crypto.Util import Counter

# Handler for serving the decrypted chunks
async def stream_mega_file(request, file_info):
    counter = Counter.new(128, initial_value=int.from_bytes(file_info['iv'], byteorder='big'))
    cipher = AES.new(file_info['key'], AES.MODE_CTR, counter=counter)
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(file_info['url']) as response:
            # Set the content type and headers for the response
            headers = {
                'Content-Type': 'application/octet-stream',
                'Content-Disposition': 'attachment; filename="{}"'.format(file_info['file_name']),
                'Content-Length': str(file_info['file_size']),
            }
            # Create a new aiohttp.web.StreamResponse object
            decrypted_response = web.StreamResponse(headers=headers)
            # Start the response
            await decrypted_response.prepare(request)
            # Stream and decrypt the chunks
            async for chunk in response.content.iter_chunked(1024):
                # AES decryption
                decrypted_chunk = cipher.decrypt(chunk)
                await decrypted_response.write(decrypted_chunk)
            # Signal the end of the response
            await decrypted_response.write_eof()
            return decrypted_response
async def handler(request):
    try:
        if request.headers.get('Range', None) is not None:
            return web.Response(status=416)
        mega_url = request.query.get("url", None)
        if mega_url is None:
            with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'main.html'), 'r') as file:
                return web.Response(text=file.read(), content_type='text/html')
        file_info = mega_file(mega_url)
        if file_info['ok']:
            return await stream_mega_file(request, file_info)
        else:
            return web.Response(text=file_info['error'])
    except Exception as e:
        return web.Response(text=repr(e))

# Create and run the aiohttp web server
app = web.Application()
app.router.add_get('/download', handler)
web.run_app(app)
