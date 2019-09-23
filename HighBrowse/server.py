ENTRIES = ['Steph was here', 'Oink was here']

def start_server():
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    s.bind(('127.0.0.1', 8000))
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
    response = handle_request(method, url, headers, body)
    response = response.encode("utf8")
    conx.send('HTTP/1.0 200 OK\r\n'.encode('utf8'))
    conx.send('Content-Length: {}\r\n\r\n'.format(len(response)).encode('utf8'))
    conx.send(response)
    conx.close()


def handle_request(method, url, headers, body):
    print('handling request for body: ', body)
    if url == "/comment.js":
        with open("comment.js") as f:
            return f.read()
    if method == 'POST':
        params = {}
        print('body is: ', body)
        for field in body.split("&"):
            name, value = field.split("=", 1)
            params[name] = value.replace("%20", " ")
        if 'guest' in params and len(params['guest']) <= 100:
            print('appending this to list: ', params['guest'])
            ENTRIES.append(params['guest'])
    out = "<!doctype html><body>"
    out += "<form action=add method=post><p><input id=guest></p><p id=errors></p><p><button>Sign the book!</button></p></form>"
    out += "<script src=/comment.js></script>"
    for entry in ENTRIES:
        out += "<p>" + entry + "</p>"
    out += "</body>"
    return out


if __name__ == "__main__":
    import socket
    print('Server running on 8000...')
    start_server()