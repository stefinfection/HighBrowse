SHOP = [{'name': 'square', 'price': 10}, {'name': 'circle', 'price': 10}, {'name': 'triangle', 'price': 15}]      # items for sale in our marketplace {name: x, price: x}
CART = []      # items in cart {name: x, quantity: x, price: x}
LOGINS = {}          # account info {username: x, password: y}
TOKENS = {}
NONCES = {}


def start_server():
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    s.bind(('127.0.0.1', 8080))
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
    #### Script requests ####
    if url == "/comment.js":
        with open("comment.js") as f:
            return {}, f.read()

    # See if we already have a username in cookies
    username = None
    if "cookie" in headers:
        username = TOKENS.get(headers["cookie"])

    #### GET requests ####
    # Get login
    if url == "/login":
        body = "<!doctype html>"
        body += "<form action=/ method=post>"
        body += "<p>Username: <input id=username></p>"
        body += "<p>Password: <input id=password type=password></p>"
        body += "<p><button>Log in</button></p>"
        body += "</form>"
        return {}, body

    # Get history
    if url == "/history":
        body = "<!doctype html>"
        # TODO: add actual items here
        body += "<p><a href=/>Back</a></p>"
        return {}, body

    # Get shop
    if url == '/checkout':
        subtotal = get_total(CART)
        tax = get_tax(CART)
        body = "<!doctype html>"
        body += "<form action=/confirm method=post>"
        body += "<p>Sub-Total: " + format_price(subtotal) + "</p>"
        body += "<p>Tax: " + format_price(tax) + "</p>"
        body += "<p>Total: " + format_price(subtotal + tax) + "</p>"
        body += "<p First Name:<input id=first_name>></input></p>"
        body += "<p Last Name:<input id=last_name>></input></p>"
        body += "<p Address:<input id=address>></input></p>"
        body += "<p Credit Card:<input id=credit_card>></input></p>"
        body += "<p Expiration Date(mm/yy):<input id=exp_date>></input></p>"
        body += "<p CVV:<input id=cvv>></input></p>"
        body += "<p><button>Complete Purchase</button></p>"
        body += "<p><a href=/></a></p>"
        body += "</form>"
        return {}, body

    # Init forms that may change from GET vs POST
    out = "<!doctype html><body>"

    # Get cart
    if url == "/cart":
        out += "<form action=/cart method=post>"

    # Get shop
    if url == "/":
        if username:
            # TODO: make this logout
            out += "<p><a href=/>Logout</a></p>"
        else:
            out += "<p><a href=/login>Login</a></p>"
        out += "<form action=/add method=post>"
        for item in SHOP:
            out += "<p>" + item.name + "</p>" \
                   "<p>" + item.price + "</p>" + \
                   "<p><button item=" + item.name + ">Add Item</button></p>" \
                   "</form><p><a href=/cart></a></p>"

    # Add nonce
    nonce = str(random.random())[2:]
    out += "<input name=nonce type=hidden value=" + nonce + ">"

    # Complete purchase or add to cart
    if method == 'POST':
        params = form_decode(body)

        # Add item to cart or clear
        if url == '/cart' and username:
            if 'item' in params:
                add_item = get_item_object(params['item'])
                CART.append(add_item)
            else:
                CART_ITEMS = []
        elif url == '/cart':
            out += '<p class=errors>Please login before adding items to cart!</p>'

        # Completing purchase
        # TODO: add permissions/nonce checks here
        elif url == '/confirm':
            out += "<p>Thank you for shopping</p>"
            out += "<a href=/>Return to store</a>"

        # Logging in
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

    # End of cart
    if url == "/cart":
        for item in CART:
            out += "<p>" + item.name + "</p>"
            out += "<p>" + item.quantity + "</p>"
            out += "<p>" + item.price + "</p>"
            # TODO: put in little image here too
        out += "<p><button>Clear Cart</button></p>"
        out += "<p><a href=/>Keep Shopping</a></p>"
        out += "<p><a href=/checkout>Proceed To Checkout</a></p>"
        out += "</form>"

    # Finish cart or shop
    out += "<form action=add method=post>"
    out += "<script src=/comment.js></script>"
    out += "</body>"
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


def get_total(items):
    total = 0
    for item in items:
        total += item['price']
    return total


def get_tax(items):
    UTAH_TAX = 0.0485
    tax_total = 0
    for item in items:
        tax_total += (item['price'] * UTAH_TAX)
    return tax_total


def format_price(price):
    return '$' + str(round(price, 2))


def get_item_object(item_name, items):
    for item in items:
        if item['name'] == item_name:
            return item

if __name__ == "__main__":
    import socket
    import random
    print('Server running on 8000...')
    start_server()