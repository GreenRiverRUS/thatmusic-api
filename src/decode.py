import base64


def _base64_based_decode(encoded: str):
    result = []
    for char in encoded:
        if char == 'O':
            result.append('0')
        elif char == '0':
            result.append('o')
        elif char.islower():
            result.append(char.upper())
        else:
            result.append(char.lower())
    encoded = ''.join(result)
    encoded += '=' * (4 - len(encoded) % 4)
    return base64.b64decode(encoded.encode()).decode()


def _get_swap_indexes(string_length, key):
    key = abs(key)
    result = []
    for i in range(string_length - 1, -1, -1):
        key = (string_length * (i + 1) ^ key + i) % string_length
        result.insert(0, key)
    return result


def _swap_decode(*args):
    string, key = args[0], int(args[1])
    if not len(string):
        return ''
    result = [char for char in string]
    swap_indexes = _get_swap_indexes(len(string), key)
    for i in range(1, len(string)):
        j = swap_indexes[len(result) - 1 - i]
        result[i], result[j] = result[j], result[i]
    return ''.join(result)


def _caesar_decode(*args):
    string, key = args[0], int(args[1])
    alphanumeric = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN0PQRSTUVWXYZO123456789+/='
    alphanumeric *= 2
    result = [char for char in string]
    for i in range(len(string) - 1, -1, -1):
        try:
            idx = alphanumeric.index(result[i])
            result[i] = alphanumeric[idx - key]
        except ValueError:
            continue
    return ''.join(result)


_command_map = {
    'v': lambda *args: args[0][::-1],
    'i': lambda *args: _command_map['s'](args[0], int(args[1]) ^ int(args[2])),
    'r': _caesar_decode,
    's': _swap_decode,
    'x': lambda *args: ''.join(chr(ord(char) ^ int(args[1])) for char in args[0])
}


# based on taken from https://vk.com/js/cmodules/web/audioplayer.js
def decode_vk_mp3_url(encoded_url: str, user_id: str):
    if not len(encoded_url) or 'audio_api_unavailable' not in encoded_url:
        return None

    encoded, key = encoded_url.split('?extra=')[1].split('#')
    if not len(key):
        return None

    decoded = _base64_based_decode(encoded)
    keys = _base64_based_decode(key).split('\t')
    for key in keys[::-1]:
        command, *args = key.split('\x0b')
        func = _command_map.get(command, None)
        args.append(user_id)
        if func is None:
            return None
        decoded = func(decoded, *args)
    if decoded.startswith('http'):
        return decoded

    return None


if __name__ == '__main__':
    print(decode_vk_mp3_url(
        'https://m.vk.com/mp3/audio_api_unavailable.mp3?'
        'extra=nuvUsJrHChz1oxfLswGZDerRzNnrs2fZDeDLnMuYz'
        'v96sMn1mZj3BJrbyJbPC1u5AI9sCLzAAfHmDf9Mrdf1ltq9'
        'l3rMttfZBO5AmhbNn184zMLsr1fyuJLnChjWngvnD3Lbowr'
        'qzvDzv1iYB2nIrwj3nY1vAY5bwtnFlxDhwtnADhHZmun2DJ'
        'iTlLv5Au5TDf9vAeO3BMCVEdDWoJDHA1b5rxHfzZ9TvY5eD'
        'ZrmD3i3AZq4luT4C1rurtGVr3vjuJfPywvVnxLI#AqS1otu',
        user_id='22718044'
    ))
