def start_server():
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    s.bind(('127.0.0.1', 8090))
    s.listen()
    while True:
        conx, addr = s.accept()
        handle_connection(conx)


def handle_connection(conx):
    req = conx.makefile("rb")
    method, url, version = req.readline().decode('utf8').split(" ", 2)
    assert method in ["GET", "POST"]
    headers = {}
    for line in req:
        line = line.decode('utf8')
        if line == '\r\n':
            break
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()
    body = ''
    if 'content-length' in headers:
        length = int(headers['content-length'])
        body = req.read(length).decode('utf8')
    else:
        body = None
    headers, response = handle_request(method, url, headers, body)
    response = response.encode("utf8")
    conx.send('HTTP/1.0 200 OK\r\n'.encode('utf8'))
    for header, value in headers.items():
        conx.send("{}: {}\r\n".format(header, value).encode('utf8'))
    conx.send('Content-Length: {}\r\n\r\n'.format(len(response)).encode('utf8'))
    conx.send(response)
    conx.close()


def handle_request(method, url, headers, body):
    if method == 'POST':
        params = form_decode(body)
        print('\n')
        print('ME WANT COOKIES (AND DATA)')
        print('            _  _')
        print('         _ /0\/ \_')
        print('  .-.  .-` \_/\\0/ \'-.')
        print(' /:::\ / ,_________,  \\')
        print('/\:::/ \  \'.(:::/  `\'-;')
        print('\ `-\'`\ \'._`\"\'\"\'\__    \\')
        print(' `\'-.  \   `)-=-=(  `,   |')
        print('     \\  `-"`      `"-`   /\'\)')
        print(params)
    out = ''
    return headers, out


def form_decode(body):
    params = {}
    if body is not None:
        for field in body.split("&"):
            name, value = field.split("=", 1)
            params[name] = value.replace("%20", " ")
    else:
        print('No body received in form_decode')
    return params


if __name__ == "__main__":
    import socket
    print('Server running on 8090...')
    start_server()