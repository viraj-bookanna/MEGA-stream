import base64,requests,json,re
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from struct import pack, unpack

def get_info(file_id, key):
    jdata = [{
        "a": "g",
        "esid": "",
        "g": 1,
        "ssl": 0,
        "p": file_id
    }]
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.93 Safari/537.36',
    }
    response = requests.post('https://g.api.mega.co.nz/cs?domain=meganz&id=0&lang=en', headers=headers, json=jdata).json()
    cipher = AES.new(key, AES.MODE_CBC, bytes.fromhex('00000000000000000000000000000000'))
    plaintext = cipher.decrypt(base64.urlsafe_b64decode(response[0]['at']+'=='))
    response[0]['at'] = json.loads(re.sub(rb'[\x00-\x1F\x80-\xFF]', b'', plaintext.replace(b'\0', b'')[4:]).decode())
    return response

def generate_key_and_iv(file_key):
    b = base64.urlsafe_b64decode(file_key + '==')
    b = b.ljust(4 * ((len(b) + 3) // 4), b'\0')
    to_key = list(unpack('!{}L'.format(len(b) // 4), b))
    to_iv = to_key[4:6] + [0, 0]
    to_key_len = len(to_key)
    if to_key_len == 4:
        k = [to_key[0], to_key[1], to_key[2], to_key[3]]
        key = pack('!4L', *k)
    elif to_key_len == 8:
        k = [to_key[0] ^ to_key[4], to_key[1] ^ to_key[5], to_key[2] ^ to_key[6], to_key[3] ^ to_key[7]]
        key = pack('!4L', *k)
    else:
        raise ValueError("Invalid key, please verify your MEGA url.")
    iv = pack('!4L', *to_iv)
    return key, iv

def mega_file(url):
    try:
        m = re.search(r'^https?://mega(?:\.co)?\.nz/file/([A-Za-z0-9_-]+)[#!]([A-Za-z0-9_-]+)$', url)
        key, iv = generate_key_and_iv(m[2])
        info = get_info(m[1], key)
        return {
            'ok': True,
            'url': info[0]['g'],
            'file_name': info[0]['at']['n'],
            'file_size': info[0]['s'],
            'key': key,
            'iv': iv,
        }
    except Exception as e:
        return {
            'ok': False,
            'error': repr(e),
        }