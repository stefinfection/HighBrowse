LOGINS = {'steph': 'rules'}          # account info {username: x, password: y}
TOKENS = {}
SHOP = [{'name': 'square', 'price': 10}, {'name': 'circle', 'price': 10}, {'name': 'triangle', 'price': 15}]
COOKIE_PLEDGE = False
INPUT_PLEDGE = False
INCLUDE_CONVERSION_SCRIPT = False


def start_server(curr_cart, port):
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    s.bind(('127.0.0.1', port))
    s.listen()
    while True:
        conx, addr = s.accept()
        handle_connection(conx, curr_cart)


def handle_connection(conx, curr_cart):
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
    headers, response = handle_request(method, url, headers, body, curr_cart)
    response = response.encode("utf8")
    conx.send('HTTP/1.0 200 OK\r\n'.encode('utf8'))
    for header, value in headers.items():
        conx.send("{}: {}\r\n".format(header, value).encode('utf8'))
    conx.send('Content-Length: {}\r\n\r\n'.format(len(response)).encode('utf8'))
    conx.send(response)
    conx.close()


def handle_request(method, url, headers, body, curr_cart):
    #### Script requests ####
    if url == "/comment.js":
        with open("comment.js") as f:
            return {}, f.read()
    elif url == "/dollarsToEuros.js":
        with open("dollarsToEuros.js") as f:
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
        body += "<p><a href=/>Back</a></p>"
        return {}, body

    # Get checkout
    if url == '/checkout':
        subtotal = get_total(curr_cart)
        tax = get_tax(curr_cart)
        body = "<!doctype html><html>"
        body += "<body>"
        body += "<form action=/confirm method=post>"
        body += "<p>Sub-Total: " + format_price(subtotal) + "</p>"
        body += "<p>Tax: " + format_price(tax) + "</p>"
        body += "<p>Total: " + format_price(subtotal + tax) + "</p>"
        body += "<p>First Name: <input id=first_name></p>"
        body += "<p>Last Name: <input id=last_name></p>"
        body += "<p>Address: <input id=address></p>"
        body += "<p>Credit Card: <input id=credit_card></p>"
        body += "<p>Expiration Date(mm/yy): <input id=exp_date></p>"
        body += "<p>CVV: <input id=cvv></p>"
        body += "<p><button>Complete Purchase</button></p>"
        body += "<p><a href=/>Back To Shop</a></p>"
        body += "</form></body></html>"
        return {}, body

    # Init forms that may change from GET vs POST
    out = "<!doctype html><html>"
    out += "<head></head><body>"

    # Get cart
    if url == "/cart":
        out += "<form action=/cart method=post>"

    # Get shop
    if url == "/":
        if username:
            out += "<p><a href=/>Logout</a></p>"
        else:
            out += "<p><a href=/login>Login</a></p>"

        out += "<p><a href=/cart>Cart</a></p>"
        out += "<p><a href=/history>Order History</a></p>"
        out += "<form action=/cart method=post>"
        for item in SHOP:
            out += "<div>"
            out += "<p>" + item['name'] + " " + format_price(item['price']) + "</p>"
            out += "<p><button id=test item=" + item['name'] + ">Add Item</button></p>"
            out += "</div>"

    # Complete purchase or add to cart
    if method == 'POST':
        params = form_decode(body)

        # Add item to cart or clear
        if url == '/cart' and username:
            if 'item' in params:
                add_item = get_item_object(params['item'], curr_cart)
                if add_item is None:
                    shop_item = get_item_object(params['item'], SHOP)
                    add_item = shop_item.copy()
                    add_item['quantity'] = 1
                    curr_cart.append(add_item)
                else:
                    add_item['quantity'] += 1
            else:
                curr_cart.clear()
        elif url == '/cart':
            out += '<p class=errors>Please login before adding items to cart!</p>'
            out += '<p><a href=/login>Go To Login</a></p>'

        # Completing purchase
        elif url == '/confirm':
            out += "<p>Thank you for shopping</p>"
            out += "<a href=/>Return to store</a>"

        # Logging in
        elif url == '/':
            if check_login(params.get("username"), params.get("password")):
                username = params.get("username")
                token = str(random.random())[2:]
                TOKENS[token] = username
                headers["set-cookie"] = "token=" + token
                out += "<p id=log_success class=success>Logged in as {}</p>".format(username)
            else:
                out += "<p id=log_fail class=errors>Login failed!</p>".format(username)

    # End of cart
    if url == "/cart" and username:
        for item in cart:
            out += "<p>" + item['name'] + ' ' + str(item['quantity']) + ' ' + format_price(item['price']) + "</p>"
        if username:
            out += "<p><button>Clear Cart</button></p>"
            out += "<p><a href=/>Keep Shopping</a></p>"
            out += "<p><a href=/checkout>Proceed To Checkout</a></p>"

    # Finish cart or shop
    out += "</form>"
    if INCLUDE_CONVERSION_SCRIPT:
        pledges = 'cookie:{},input:{}'.format(COOKIE_PLEDGE, INPUT_PLEDGE)
        pledges = '{' + pledges + '}'
        out += "<script src=/dollarsToEuros.js pledge={}></script>".format(pledges)
    out += "</body></html>"
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
    if body is not None:
        for field in body.split("&"):
            name, value = field.split("=", 1)
            params[name] = value.replace("%20", " ")
    else:
        print('No body received in form_decode')
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
    return None

if __name__ == "__main__":
    import socket
    import random
    import sys
    cart = []
    port = sys.argv[1]
    if port is None:
        print('Please enter port')
    else:
        print('Server running on {}...'.format(port))
    # Set globals
    INCLUDE_CONVERSION_SCRIPT = sys.argv[2] == 'True'
    COOKIE_PLEDGE = sys.argv[3] == 'True'
    INPUT_PLEDGE = sys.argv[4] == 'True'
    start_server(cart, int(port))
