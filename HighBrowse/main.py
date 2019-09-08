import socket
import tkinter
import tkinter.font
from dataclasses import dataclass
from dataclasses import field
from typing import List, Tuple


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
    parent: 'ElementNode'
    attributes: {}


@dataclass
class TextNode:
    text: str
    parent: 'TextNode'


@dataclass
class BlockLayout:
    parent: 'BlockLayout' or 'Page'
    node: ElementNode or TextNode
    children: List['BlockLayout' or 'InlineLayout'] = field(default_factory=list)
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0

    def __post_init__(self):
        if type(self.parent) is not None:
            self.parent.children.append(self)
            self.x = self.parent.x
            self.w = self.parent.w
        if type(self.parent) is BlockLayout:
            self.y = self.parent.y + self.parent.h
        elif type(self.parent) is Page:
            self.y = self.parent.y

    def layout(self):
        y = self.y
        if any(is_inline(child) for child in self.node.children):
            layout = InlineLayout(parent=self)
            layout.layout(self.node)
            y += layout.get_height()
            self.h = y - self.y
        else:
            for child in self.node.children:
                if isinstance(child, TextNode) and child.text.isspace():
                    continue
                layout = BlockLayout(parent=self, node=child)
                layout.layout()
                y += layout.get_height()
                self.h = y - self.y


    def get_height(self):
        return self.h

    def get_display_list(self):
        dl = []
        for child in self.children:
            dl.extend(child.get_display_list())
        return dl


@dataclass
class InlineLayout:
    parent: BlockLayout
    dl: List[Tuple[int, int, str, tkinter.font.Font]] = field(default_factory=list)
    x: int = 0
    y: int = 0
    bold_count: int = 0
    italic_count: int = 0
    terminal_space: bool = True

    def __post_init__(self):
        if type(self.parent) is not None:
            self.x = self.parent.x
            self.parent.children.append(self)
        if type(self.parent) is BlockLayout:
            self.y = self.parent.y + self.parent.h
        elif type(self.parent) is Page:
            self.y = self.parent.y

    # Lays out the argument node, and all of its descendants.
    def layout(self, node):
        if isinstance(node, ElementNode):
            self.open(node)
            for child in node.children:
                self.layout(child)
            self.close(node)
        else:
            self.text(node)

    # Updates the styling and spacing state of this, according to the open tag node argument.
    def open(self, node):
        if node.tag == "i":
            self.italic_count += 1
        elif node.tag == "b":
            self.bold_count += 1
        elif node.tag == "br":
            self.x = 13
            self.y += self.get_font().metrics("linespace") * 1.2

    # Updates the styling and spacing state of this, according to the closing tag node argument.
    def close(self, node):
        if node.tag == "i":
            self.italic_count -= 1
        elif node.tag == "b":
            self.bold_count -= 1
        elif node.tag == "p":
            self.terminal_space = True
            self.x = 13
            self.y += self.get_font().metrics("linespace") * 1.2 + 16

    # Lays out the provided text node within the x & y bounds of its parent.
    def text(self, node):
        font = self.get_font()

        # account for entry space if present
        if node.text[0].isspace() and not self.terminal_space:
            self.x += font.measure(" ")

        # populate display list
        words = node.text.split()
        for i, word in enumerate(words):
            w = font.measure(word)
            # check if we need to line break
            if self.x + w > self.parent.x + self.parent.w:
                self.y += font.metrics("linespace") * 1.2
                self.x = self.parent.x

            self.dl.append((self.x, self.y, word, font))

            # update x to include word width AND a space if we're not at the end of the line
            self.x += w + (0 if i == len(words) - 1 else font.measure(" "))

        # update x to include a whitespace if last char in line really is one
        self.terminal_space = node.text[-1].isspace()
        if self.terminal_space and words:
            self.x += font.measure(" ")

    # Returns the height of this.
    def get_height(self):
        font = self.get_font()
        return self.y + font.metrics("linespace") * 1.2 - self.parent.y

    # Returns this display list.
    def get_display_list(self):
        return self.dl

    # Returns the font based on the bold and italic class variables.
    def get_font(self):
        fonts = {  # (bold, italic) -> font
            (False, False): tkinter.font.Font(family="Times", size=16),
            (True, False): tkinter.font.Font(family="Times", size=16, weight="bold"),
            (False, True): tkinter.font.Font(family="Times", size=16, slant="italic"),
            (True, True): tkinter.font.Font(family="Times", size=16, weight="bold", slant="italic"),
        }
        return fonts[self.bold_count > 0, self.italic_count > 0]


@dataclass
class Page:
    children: []
    x: int = 13
    y: int = 13
    w: int = 774


# Parses the host, port, path, and fragment components of the provided url, if they exist.
# Reports an error if the argument does not start with http://
# Defaults to port 80 if none provided.
def parse(url):
    assert url.startswith("http://")
    url = url[len("http://"):]
    host_port, path_fragment = url.split("/", 1) if "/" in url else (url, "")
    host, port = host_port.rsplit(":", 1) if ":" in host_port else (host_port, "80")
    path, fragment = ("/" + path_fragment).rsplit("#", 1) if "#" in path_fragment else ("/" + path_fragment, None)
    return host, int(port), path, fragment


# Returns the header and body responses obtained from the provided host and path arguments.
# Reports an error if anything but a 200/OK status obtained from the host.
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


# Returns a list of Text and Tag objects according to the provided source argument.
def lex(source):
    out = []
    text = ""
    for c in source:
        # just finished text piece, append to list & reset
        if c == "<":
            if text:
                out.append(Text(text=text))
            text = ""
        # just finished tag piece, append to list & reset
        elif c == ">":
            if text:
                out.append(Tag(tag=text, isClose=text.startswith("/")))
            text = ""
        else:
            text += c
    return out


# Creates node tree for Text and Tags in HTML document.
def populate_tree(tokens):
    current_node = None
    for tok in tokens:
        if isinstance(tok, Text):
            # create child node and add it to parent
            child = TextNode(tok.text, current_node)
            current_node.children.append(child)
        elif isinstance(tok, Tag):
            if not tok.isClose:
                # Split out attributes
                tag_name, *attrs = tok.tag.split(" ")
                attr_obj = {}
                for attr in attrs:
                    out = attr.split("=", 1)
                    name = out[0]
                    val = out[1].strip("\"") if len(out) > 1 else ""
                    attr_obj[name.lower()] = val

                # Create element node
                child = ElementNode(tag_name, [], current_node, attr_obj)
                if current_node is not None:
                    current_node.children.append(child)

                # Shift our current node if we're not looking at a self-closing tag
                if child.tag not in ["br", "link", "meta"]:
                    current_node = child
            else:
                tag = tok.tag[1:]  # strip off closing tag /
                node = current_node
                while node is not None and node.tag != tag:
                    node = node.parent

                # If we couldn't find a matching open tag, just bump up to last tag
                if not node and current_node.parent is not None:
                    current_node = current_node.parent
                # Otherwise, bump up from found matching tag
                elif node.parent is not None:
                    current_node = node.parent

    return current_node


# Returns true if node argument is TextNode or ElementNode and a bold or italic tag.
def is_inline(node):
    return (isinstance(node, TextNode) and not node.text.isspace()) or \
           (isinstance(node, ElementNode) and node.tag in ["b", "i"])


# Renders the provided nodes. Binds scrolling keys.
def show(head_node):
    window = tkinter.Tk()
    canvas = tkinter.Canvas(window, width=800, height=600)
    canvas.pack()

    SCROLL_STEP = 100
    scroll_y = 0
    page_padding = 13
    window_height = 600

    page = Page(children=[])
    mode = BlockLayout(parent=page, node=head_node)
    mode.layout()
    max_h = mode.get_height()
    display_list = mode.get_display_list()

    def render():
        canvas.delete("all")
        for x, y, w, f in display_list:
            canvas.create_text(x, y - scroll_y, text=w, font=f, anchor='nw')

    def scroll_down(e):
        nonlocal scroll_y
        scroll_y = min(scroll_y + SCROLL_STEP, page_padding + max_h - window_height)
        render()

    def scroll_up(e):
        nonlocal scroll_y
        scroll_y = max(scroll_y - SCROLL_STEP, 0)
        render()

    window.bind("<Down>", scroll_down)
    window.bind("<Up>", scroll_up)
    render()
    tkinter.mainloop()


# Gets the show on the road.
def run(url):
    host, port, path, fragment = parse(url)
    headers, body = request(host, port, path)
    text = lex(body)
    nodes = populate_tree(text)
    show(nodes)


if __name__ == "__main__":
    import sys
    run(sys.argv[1])

