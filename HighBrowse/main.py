import socket
import tkinter
import tkinter.font
from dataclasses import dataclass


@dataclass
class Text:
    text: str


@dataclass
class Tag:
    tag: str
    isClose: bool


@dataclass
class ElementNode:
    tag: str
    children: []
    parent: None
    attributes: {}


@dataclass
class TextNode:
    text: str
    parent: None


def parse(url):
    assert url.startswith("http://")
    url = url[len("http://"):]
    hostport, pathfragment = url.split("/", 1) if "/" in url else (url, "")
    host, port = hostport.rsplit(":", 1) if ":" in hostport else (hostport, "80")
    path, fragment = ("/" + pathfragment).rsplit("#", 1) if "#" in pathfragment else ("/" + pathfragment, None)
    return host, int(port), path, fragment


def request(host, port, path):
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    s.connect((host, port))
    s.send("GET {} HTTP/1.0\r\nHost: {}\r\n\r\n".format(path, host).encode("utf8"))
    response = s.makefile("rb").read().decode("utf8")
    s.close()

    head, body = response.split("\r\n\r\n", 1)
    lines = head.split("\r\n")
    version, status, explanation = lines[0].split(" ", 2)
    assert status == "200", "Server error {}: {}".format(status, explanation)
    headers = {}
    for line in lines[1:]:
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()
    return headers, body


def lex(source):
    out = []
    text = ""
    open = True
    for c in source:
        # Just finished text piece, append to list
        if c == "<":
            if text:
                out.append(Text(text=text))
            text = ""
        # Just finished tag piece, append to list & reset
        elif c == ">":
            if text:
                out.append(Tag(tag=text, isClose=text.startswith("/")))
            text = ""
        else:
            text += c
    return out


# Creates node tree for text and tags in HTML document.
def populate_tree(tokens):
    currentNode = None
    for tok in tokens:
        if isinstance(tok, Text):
            # create child node and add it to parent
            child = TextNode(tok.text, currentNode)
            currentNode.children.append(child)
        elif isinstance(tok, Tag):
            if not tok.isClose:
                # Split out attributes
                tagName, *attrs = tok.tag.split(" ")
                attrObj = {}
                for attr in attrs:
                    out = attr.split("=", 1)
                    name = out[0]
                    val = out[1].strip("\"") if len(out) > 1 else ""
                    attrObj[name.lower()] = val

                # Create element node
                child = ElementNode(tagName, [], currentNode, attrObj)
                if currentNode is not None:
                    currentNode.children.append(child)

                # Shift our current node if we're not looking at a self-closing tag
                if child.tag not in ["br", "link", "meta"]:
                    currentNode = child
            else:
                tag = tok.tag[1:]  # strip off closing tag /
                node = currentNode
                while node is not None and node.tag != tag:
                    node = node.parent

                # If we couldn't find a matching open tag, just bump up to last tag
                if not node and currentNode.parent is not None:
                    currentNode = currentNode.parent
                # Otherwise, bump up from found matching tag
                elif node.parent is not None:
                    currentNode = node.parent

    return currentNode


def get_font(bold, italic):
    fonts = {  # (bold, italic) -> font
        (False, False): tkinter.font.Font(family="Times", size=16),
        (True, False): tkinter.font.Font(family="Times", size=16, weight="bold"),
        (False, True): tkinter.font.Font(family="Times", size=16, slant="italic"),
        (True, True): tkinter.font.Font(family="Times", size=16, weight="bold", slant="italic"),
    }
    return fonts[bold, italic]


# A recursive function which takes in a tree node and a state holding x, y, bold, italic, terminal space states.
# For each child provided in the element node, layout will be called again and the state updated accordingly.
def layout(node, state):
    if isinstance(node, ElementNode):
        state = layout_open(node, state)
        for child in node.children:
            state = layout(child, state)
        state = layout_close(node, state)
    else:
        state = layout_text(node, state)
    return state


# Sets current layout state based on the open tag provided
def layout_open(node, state):
    x, y, bold_count, italic_count, terminal_space, display_list = state

    if node.tag == "i":
        italic_count += 1
    elif node.tag == "b":
        bold_count += 1
    elif node.tag == "br":
        x = 13
        y += (get_font(bold_count > 0, italic_count > 0)).metrics("linespace") * 1.2

    return x, y, bold_count, italic_count, terminal_space, display_list


# Sets the current layout state based on the close tag provided
def layout_close(node, state):
    # print("Close called: ", node.tag, "\n")
    x, y, bold_count, italic_count, terminal_space, display_list = state

    if node.tag == "i":
        italic_count -= 1
    elif node.tag == "b":
        bold_count -= 1
    elif node.tag == "p":
        terminal_space = True
        x = 13
        y += (get_font(bold_count > 0, italic_count > 0)).metrics("linespace") * 1.2 + 16

    return x, y, bold_count, italic_count, terminal_space, display_list


# Utilizes the current layout state to create a display list entry for the text provided
def layout_text(node, state):
    x, y, bold_count, italic_count, terminal_space, display_list = state
    font = get_font(bold_count > 0, italic_count > 0)

    # account for entry space if present
    if node.text[0].isspace() and not terminal_space:
        x += font.measure(" ")

    # iterate through words on line
    words = node.text.split()

    for i, word in enumerate(words):
        w = font.measure(word)
        if x + w >= 787:
            y += font.metrics("linespace") * 1.2
            x = 13
        display_list.append((x, y, word, font))

        # update x to include word width AND a space if we're not at the end of the line
        x += w + (0 if i == len(words) - 1 else font.measure(" "))

    # udpate x to include a whitespace if last char in line really is one
    terminal_space = node.text[-1].isspace()
    if terminal_space and words:
        x += font.measure(" ")

    return x, y, bold_count, italic_count, terminal_space, display_list


def show(nodes):
    window = tkinter.Tk()
    canvas = tkinter.Canvas(window, width=800, height=600)
    canvas.pack()

    SCROLL_STEP = 100
    scrolly = 0
    state = (13, 13, 0, 0, True, [])
    _, _, _, _, _, display_list = layout(nodes, state)

    def render():
        canvas.delete("all")
        for x, y, w, f in display_list:
            canvas.create_text(x, y - scrolly, text=w, font=f, anchor='nw')

    def scrolldown(e):
        nonlocal scrolly
        scrolly += SCROLL_STEP
        render()

    def scrollup(e):
        nonlocal scrolly
        scrolly -= SCROLL_STEP
        render()

    window.bind("<Down>", scrolldown)
    window.bind("<Up>", scrollup)
    render()

    tkinter.mainloop()


def run(url):
    host, port, path, fragment = parse(url)
    headers, body = request(host, port, path)
    text = lex(body)
    nodes = populate_tree(text)
    show(nodes)

if __name__ == "__main__":
    import sys
    run(sys.argv[1])

