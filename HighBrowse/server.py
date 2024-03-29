ENTRIES = [ ("Mess with the best, die like the rest", "crashoverride"), ("HACK THE PLANET!!!", "nameless") ]
LOGINS = { "crash": "0cool", "nameless": "cerealkiller" }
TOKENS = {}
NONCES = {}


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
    headers, response = handle_request(method, url, headers, body)
    response = response.encode("utf8")
    conx.send('HTTP/1.0 200 OK\r\n'.encode('utf8'))
    for header, value in headers.items():
        conx.send("{}: {}\r\n".format(header, value).encode('utf8'))
    conx.send('Content-Length: {}\r\n\r\n'.format(len(response)).encode('utf8'))
    conx.send(response)
    conx.close()


def handle_request(method, url, headers, body):
    # Return js
    if url == "/comment.js":
        with open("comment.js") as f:
            return {}, f.read()

    # Route to login
    if url == "/login":
        body = "<!doctype>"
        body += "<form action=/ method=post>"
        body += "<p>Username: <input id=username></p>"
        body += "<p>Password: <input id=password type=password></p>"
        body += "<p><button>Log in</button></p>"
        body += "</form>"
        return {}, body

    # See if we already have a username in cookies
    username = None
    if "cookie" in headers:
        username = TOKENS.get(headers["cookie"])
    out = "<!doctype html><body>"

    # Add nonce
    nonce = str(random.random())[2:]
    out += "<input name=nonce type=hidden value=" + nonce + ">"

    if method == 'POST':
        params = form_decode(body)
        # posting a new guest book entry
        if url == '/add':
            if 'guest' in params and len(params['guest']) <= 100 and username \
                    and 'nonce' in params and params['nonce'] == NONCES[username]:
                ENTRIES.append((params['guest'], username))
            else:
                out += '<p class=errors>Could not add entry - must be logged in first!</p>'
        # logging in to site
        elif url == '/':
            if check_login(params.get("username"), params.get("password")):
                username = params.get("username")
                token = str(random.random())[2:]
                TOKENS[token] = username
                NONCES[username] = nonce
                headers["set-cookie"] = "token=" + token
                out += "<p class=success>Logged in as {}</p>".format(username)
            else:
                out += "<p class=errors>Login failed!</p>".format(username)

    # Always show who has signed book
    out += "<form action=add method=post><p id=input_p><input id=guest></p><p id=errors></p><p id=button_p><button>Sign the book!</button></p></form>"
    out += "<script src=/comment.js></script>"
    for entry, who in ENTRIES:
        entry = entry.replace("&", "&amp;").replace("<", "&lt;").replace("\"", "&quot;")
        out += "<p id={}_p>".format(entry) + entry + " <i>from " + who + "</i></p>"

    if username is None:
        out += "<p><a href=/login>Log in to add to the guest list</a></p>"

    out += "</body>"
    print("about to return headers from server: ", headers)
    return headers, out


def check_login(username, pw):
    return username in LOGINS and LOGINS[username] == pw


def parse_cookies(s):
    out = {}
    for cookie in s.split(";"):
        k, v = cookie.strip().split("=", 1)
        out[k] = v
    return out


def form_decode(body):
    params = {}
    for field in body.split("&"):
        name, value = field.split("=", 1)
        params[name] = value.replace("%20", " ")
    return params


if __name__ == "__main__":
    import socket
    import random
    print('Server running on 8000...')
    start_server()