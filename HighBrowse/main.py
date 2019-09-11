import socket
import tkinter
import tkinter.font
from dataclasses import dataclass
from dataclasses import field
from typing import List


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
    style: {} = None
    show_bullet: bool = False

    def __post_init__(self):
        self.style = self.compute_style()

    def compute_style(self):
        style = {}
        style_value = self.attributes.get("style", "")
        for line in style_value.split(";"):
            if line != "":
                prop, val = line.split(":")
                style[prop.lower().strip()] = val.strip()
        return style


@dataclass
class TextNode:
    text: str
    parent: 'TextNode'


@dataclass
class BlockLayout:
    parent: 'BlockLayout' or 'Page'
    node: ElementNode
    children: List['BlockLayout' or 'InlineLayout'] = field(default_factory=list)
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    mt: int = 0
    mr: int = 0
    mb: int = 0
    ml: int = 0
    pt: int = 0
    pr: int = 0
    pb: int = 0
    pl: int = 0
    bt: int = 0
    br: int = 0
    bb: int = 0
    bl: int = 0

    def __post_init__(self):
        if isinstance(self.node, ElementNode):
            # get margins
            self.mt = strip_px(self.node.style.get("margin-top", "0px"))
            self.mb = strip_px(self.node.style.get("margin-bottom", "0px"))
            self.ml = strip_px(self.node.style.get("margin-left", "0px"))
            self.mr = strip_px(self.node.style.get("margin-right", "0px"))

            # get padding
            self.pt = strip_px(self.node.style.get("padding-top", "0px"))
            self.pb = strip_px(self.node.style.get("padding-bottom", "0px"))
            self.pl = strip_px(self.node.style.get("padding-left", "0px"))
            self.pr = strip_px(self.node.style.get("padding-right", "0px"))

            # borders
            self.bt = strip_px(self.node.style.get("border-top", "0px"))
            self.bb = strip_px(self.node.style.get("border-bottom", "0px"))
            self.bl = strip_px(self.node.style.get("border-left", "0px"))
            self.br = strip_px(self.node.style.get("border-right", "0px"))

        if type(self.parent) is not None:
            self.parent.children.append(self)
        if type(self.parent) is BlockLayout:
            self.x = self.parent.content_left()
            self.y = self.parent.y + self.parent.h
            self.w = self.parent.content_width()
            if self.parent.node.tag == "li":
                self.node.show_bullet = True
        elif type(self.parent) is Page and self.w == 0:
            self.w = self.parent.w

        if isinstance(self.node, ElementNode):
            if self.node.tag == "div" and "id" in self.node.attributes \
                    and self.node.attributes["id"] == "content":
                self.w = 550
                self.pl = self.pr = 10
                self.y = self.parent.content_top()
            elif self.node.tag == "div" and "id" in self.node.attributes \
                    and self.node.attributes["id"] == "preamble":
                self.w = 190
                self.pr = 10
                self.x = self.parent.content_width() - self.w

    def layout(self):
        assign5 = False
        y = self.y
        if any(is_inline(child) for child in self.node.children):
            layout = InlineLayout(parent=self)
            layout.layout(self.node)
            y += layout.get_height()
            self.h = y - self.y
        else:
            # check to see if first child top margin overlaps with this top margin
            # if so, adjust the y coordinate of first child
            i = 0
            while i < len(self.node.children):
                first_child = self.node.children[i]
                i += 1
                if isinstance(first_child, TextNode) and first_child.text.isspace():
                    continue
                else:
                    layout = BlockLayout(parent=self, node=first_child)
                    if self.mt > 0 and layout.mt > 0 and assign5 is True:
                        min_m = min(self.mt, layout.mt)
                        layout.y -= min_m
                    layout.layout()
                    layout_height = layout.get_height() + layout.pt + layout.pb + layout.bt + layout.bb + layout.mt + layout.mb
                    y += layout_height
                    self.x += layout.ml
                    self.w -= layout.ml - layout.mr
                    self.h = y - self.y
                    break

            # layout subsequent children if there are any
            if i < len(self.node.children):
                for j in range(i, len(self.node.children)):
                    # check to see if this child's top margin can overlap with last child's bottom margin
                    # if so, adjust the y coordinate of child
                    child = self.node.children[j]
                    if isinstance(child, TextNode) and child.text.isspace():
                        continue
                    layout = BlockLayout(parent=self, node=child)
                    prev_layout = self.children[-1]
                    if isinstance(prev_layout, BlockLayout) and prev_layout.mb > 0 \
                            and isinstance(layout, BlockLayout) and layout.mt > 0 and assign5 is True:
                        layout.y -= min(prev_layout.mb, layout.mt)

                    layout.layout()
                    layout_height = layout.get_height() + layout.pt + layout.pb + layout.bt + layout.bb + layout.mt + layout.mb
                    y += layout_height
                    self.x += layout.ml
                    self.w -= layout.ml - layout.mr
                    self.h = y - self.y

                # check to see if last child bottom margin overlaps with this bottom margin
                # if so, adjust the height of this layout
                last_layout = self.children[-1]
                if isinstance(last_layout, BlockLayout) \
                        and last_layout.mb > 0 and self.mb > 0 and assign5 is True:
                    self.h -= min(last_layout.mb, self.mb)

    def get_height(self):
        return self.h

    def get_display_list(self):
        dl = []
        for child in self.children:
            if self.bl > 0:
                dl.append(DrawRect(self.x, self.y, self.x + self.bl, self.y + self.h, self.node.style.get("border-color", "black"),
                                   self.node.style.get("background-color", "")))
            if self.br > 0:
                dl.append(
                    DrawRect(self.x + self.w - self.br, self.y, self.x + self.w, self.y + self.h, self.node.style.get("border-color", "black"),
                             self.node.style.get("background-color", "")))
            if self.bt > 0:
                dl.append(DrawRect(self.x, self.y, self.x + self.w, self.y + self.bt, self.node.style.get("border-color", "black"),
                                   self.node.style.get("background-color", "")))
            if self.bb > 0:
                dl.append(
                    DrawRect(self.x, self.y + self.h - self.bb, self.x + self.w, self.y + self.h, self.node.style.get("border-color", "black"),
                             self.node.style.get("background-color", "")))
            if self.node.style.get("background-color", "") != "":
                dl.append(DrawRect(self.x, self.y, self.block_width(), self.block_height(), self.node.style.get("border-color", ""), self.node.style["background-color"]))
            dl.extend(child.get_display_list())
        return dl

    def content_left(self):
        return self.x + self.bl + self.pl

    def content_right(self):
        return self.x + self.br + self.pr

    def content_top(self):
        return self.y + self.bt + self.pt

    def content_bottom(self):
        return self.y + self.bb + self.pb

    def content_width(self):
        return self.w - self.bl - self.br - self.pl - self.pr

    def content_height(self):
        return self.h - self.bb - self.bt - self.pb - self.pt

    def block_width(self):
        return self.x + self.w

    def block_height(self):
        return self.y + self.h


@dataclass
class InlineLayout:
    parent: BlockLayout
    dl: List['DrawText' or 'DrawRect'] = field(default_factory=list)
    x: int = 0
    y: int = 0
    bold_count: int = 0
    italic_count: int = 0
    terminal_space: bool = True

    def __post_init__(self):
        if type(self.parent) is not None:
            self.parent.children.append(self)
        if type(self.parent) is BlockLayout:
            self.x = self.parent.content_left()
            self.y = self.parent.content_top() + self.parent.h
        elif type(self.parent) is Page:
            self.x = self.parent.x
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
            self.x = self.parent.x
            self.y += self.get_font().metrics("linespace") * 1.2
        elif node.tag == "li" or node.show_bullet is True:
            self.x = self.parent.x
            self.dl.append(DrawRect(self.x, self.y + self.get_font().metrics("linespace") * 0.5 - 2, self.x + 4, self.y + self.get_font().metrics("linespace") * 0.5 + 2, "black", "black"))
            self.x += self.get_font().measure("  ") + 4

    # Updates the styling and spacing state of this, according to the closing tag node argument.
    def close(self, node):
        if node.tag == "i":
            self.italic_count -= 1
        elif node.tag == "b":
            self.bold_count -= 1
        elif node.tag == "li":
            self.x = self.parent.x

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
            if self.x + w > self.parent.content_left() + self.parent.content_width():
                self.y += font.metrics("linespace") * 1.2
                self.x = self.parent.content_left()

            self.dl.append(DrawText(self.x, self.y, word, font))

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
    x: int = 0
    y: int = 0
    w: int = 787


@dataclass
class DrawText:
    x: int
    y: int
    text: str
    font: tkinter.font.Font

    def draw(self, scroll_y, canvas):
        canvas.create_text(self.x, self.y - scroll_y, text=self.text, font=self.font, anchor='nw')


@dataclass
class DrawRect:
    x1: int
    y1: int
    x2: int
    y2: int
    outline: str
    background: str

    def draw(self, scroll_y, canvas):
        if self.background != "":
            canvas.create_rectangle(self.x1, self.y1 - scroll_y, self.x2, self.y2 - scroll_y, width=0, fill=self.outline)
        canvas.create_rectangle(self.x1, self.y1 - scroll_y, self.x2, self.y2 - scroll_y, width=0, fill=self.outline)


@dataclass(frozen=True)
class TagSelector:
    tag: str

    def matches(self, node):
        return self.tag == node.tag

    @staticmethod
    def score():
        return 1


@dataclass(frozen=True)
class ClassSelector:
    clazz: str

    # TODO: this code doesn't make sense to me
    def matches(self, node):
        return self.clazz == node.attributes.get("class", "").split()

    @staticmethod
    def score():
        return 16


@dataclass(frozen=True)
class IdSelector:
    id: str

    def matches(self, node):
        return self.id == node.attributes.get("id", "").split()

    @staticmethod
    def score():
        return 256


# CSS parsing
def css_value(s, i):
    j = i
    while s[j].isalnum() or s[j] == "-" or s[j] == "#":
        j += 1
    return s[i:j], j


def css_pair(s, i):
    prop, i = css_value(s, i)
    i = css_whitespace(s, i)
    assert s[i] == ":"
    i = css_whitespace(s, i + 1)
    val, i = css_value(s, i)
    print("value is ", val)
    return (prop, val), i


def css_whitespace(s, i):
    doc_len = len(s)
    while i < doc_len and s[i].isspace():
        i += 1
    return i


# Takes in a string and an index to begin parsing
# Iterates through the provided CSS string until it has parsed a single complete rule
# Returns an object of key-value pairs representing the rules, and the index we left off at
def css_body(s, i):
    pairs = {}
    assert s[i] == "{"
    i = css_whitespace(s, i+1)
    while True:
        if s[i] == "}":
            break
        try:
            (prop, val), i = css_pair(s, i)
            pairs[prop] = val
            i = css_whitespace(s, i)
            assert s[i] == ";"
            i = css_whitespace(s, i+1)
        except AssertionError:
            while s[i] not in [";", "}"]:
                i += 1
            if s[i] == ";":
                i = css_whitespace(s, i + 1)
    assert s[i] == "}"
    return pairs, i+1


def css_selector(s, i):
    if s[i] == "#":
        name, i = css_value(s, i + 1)
        return IdSelector(name), i
    elif s[i] == ".":
        name, i = css_value(s, i + 1)
        return ClassSelector(name), i
    else:
        name, i = css_value(s, i)
        return TagSelector(name), i


# Parses the entire CSS file and returns a list of selector: rule pairs
def parse_css(doc):
    i = 0
    rule_pairs = []
    while i < len(doc):
        i = css_whitespace(doc, i)
        if i >= len(doc):
            break
        selector, i = css_selector(doc, i)
        i = css_whitespace(doc, i)
        rules, i = css_body(doc, i)
        rule_pairs.append([selector, rules])

    return rule_pairs


def apply_styles(node, rules):
    if not isinstance(node, ElementNode):
        return
    # apply css styles
    for selector, pairs in rules:
        if selector.matches(node):
            for prop in pairs:
                node.style[prop] = pairs[prop]
    # apply inline styles
    for prop, value in node.compute_style().items():
        node.style[prop] = value
    for child in node.children:
        apply_styles(child, rules)


def get_browser_styles():
    with open("default.css") as f:
        browser_style = f.read()
        browser_rules = parse_css(browser_style)
        browser_rules.sort(key=lambda x: x[0].score())
        return browser_rules


def find_style_links(node, listee):
    if not isinstance(node, ElementNode):
        return
    if node.tag == "link" and \
            node.attributes.get("rel", "") == "stylesheet" and \
            "href" in node.attributes:
        listee.append(node.attributes["href"])
    for child in node.children:
        find_style_links(child, listee)
    return listee


# Networking Stuff
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


def parse_relative_url(url, current):
    if url.startswith("http://"):
        return parse(url)

    host, port, path, fragment = parse(current)
    if url.startswith("/"):
        path, fragment = url.split("#", 1) if "#" in url else (url, None)
        return host, port, path, fragment
    else:
        path, fragment = url.split("#", 1) if "#" in url else (url, None)
        curdir, curfile = current.rsplit("/", 1)
        return host, port, curdir + "/" + path, fragment


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


# Node Stuff Creates node tree for Text and Tags in HTML document.
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


# Assumes we always have a valid Npx string as an argument
def strip_px(px):
    pieces = px.split("px")
    if len(pieces) > 0:
        return int(pieces[0])


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
        for cmd in display_list:
            cmd.draw(scroll_y, canvas)

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


# Run Stuff
# Gets the show on the road.
def run(url):
    host, port, path, fragment = parse(url)
    headers, body = request(host, port, path)
    text = lex(body)
    nodes = populate_tree(text)

    browser_rules = get_browser_styles()
    apply_styles(nodes, browser_rules)

    user_rules = []
    for link in find_style_links(nodes, []):
        l_host, l_port, l_path, l_fragment = parse_relative_url(link, url)
        header, body = request(l_host, l_port, l_path)
        l_rules = parse_css(body)
        user_rules.extend(l_rules)
    user_rules.sort(key=lambda x: x[0].score())
    apply_styles(nodes, user_rules)

    show(nodes)


if __name__ == "__main__":
    import sys
    run(sys.argv[1])
