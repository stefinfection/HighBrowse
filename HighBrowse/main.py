import socket
import tkinter
import tkinter.font
import dukpy
import time
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
    handle: int = 0
    pseudoClasses: set = None

    def __post_init__(self):
        self.style = self.compute_style()
        self.pseudoClasses = set()

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
    parent: 'TextNode'      # guaranteed to always have a parent
    style: {} = None

    def __post_init__(self):
        self.style = {}


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
        if self.node is not None and any(is_inline(child) for child in self.node.children):
            layout = InlineLayout(parent=self, node=self.node)
            layout.layout()
            y += layout.get_height()
            self.h = y - self.y
        elif self.node is not None:
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
                print('Applying a border to {} because parent {} has border \n\n'.format(child.node.attributes.get('id', 'NO_ID'), self.node.attributes.get('id', 'NO_ID')))
                # FIXME parent id is same as child id...
                dl.append(
                    DrawRect(self.x, self.y + self.h - self.bb, self.x + self.w, self.y + self.h, self.node.style.get("border-color", "black"),
                             self.node.style.get("background-color", "")))
            if self.node.style.get("background-color", "") != "":
                dl.append(DrawRect(self.x, self.y + self.mt, self.block_width(), self.block_height(), self.node.style.get("border-color", ""), self.node.style["background-color"]))
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
        return self.y + self.h + self.pb + self.pt


@dataclass
class InputLayout:
    node: TextNode or ElementNode
    multiline: bool = False
    parent: 'LineLayout' = None
    post_space_width: int = 0
    children: List['InlineLayout'] = field(default_factory=list)
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0

    def __post_init__(self):
        self.w = 200
        self.h = 60 if self.multiline else 20

    def layout(self, x, y):
        self.x = x
        self.y = y
        for child in self.node.children:
            layout = InlineLayout(self, child)
            layout.layout()

    def attach(self, parent):
        self.parent = parent
        parent.children.append(self)
        parent.w += self.w

    def add_space(self):
        if self.post_space_width == 0:
            gap = 5
            self.post_space_width = gap
            self.parent += gap

    def get_display_list(self):
        border = DrawRect(self.x, self.y, self.x + self.w, self.y + self.h, outline='', background='')
        if self.children:
            dl = [border]
            for child in self.children:
                dl.extend(child.get_display_list())
            return dl
        else:
            font = tkinter.font.Font(family='Times', size=16)
            text = DrawText(self.x+1, self.y+1, (self.node.attributes.get('value', '')), 'black', font)
            return [border, text]

    def get_height(self):
        return self.h

    def content_left(self):
        return self.x + 1

    def content_top(self):
        return self.y + 1

    def content_width(self):
        return self.w - 2


# Represents a single word
@dataclass
class TextLayout:
    node: TextNode
    text: str
    parent: 'LineLayout' = None
    children: List[bool] = field(default_factory=list)
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    color: str = 'black'
    font: tkinter.font.Font = None
    post_space_width: int = 0

    def __post_init__(self):
        is_bold = self.node.style['font-weight'] == 'bold'
        is_italic = self.node.style['font-style'] == 'italic'
        self.color = self.node.style['color']
        self.font = tkinter.font.Font(
            family="Times", size=16,
            weight="bold" if is_bold else "normal",
            slant="italic" if is_italic else "roman"
        )
        self.w = self.font.measure(self.text)
        self.h = self.font.metrics('linespace')

    def layout(self, x, y):
        self.x = x
        self.y = y

    def attach(self, parent):
        self.parent = parent
        parent.children.append(self)
        parent.w += self.w

    def add_space(self):
        if self.post_space_width == 0:
            gap = self.font.measure(" ")
            self.post_space_width = gap
            self.parent.w += gap

    def get_display_list(self):
        return [DrawText(self.x, self.y, self.text, self.color, self.font)]

    @staticmethod
    def get_height():
        return 0

# Represents a single line of text
@dataclass
class LineLayout:
    parent: 'InlineLayout'
    children: List['TextLayout' or 'InputLayout'] = field(default_factory=list)
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0

    def __post_init__(self):
        self.parent.children.append(self)

    def layout(self, y):
        self.y = y
        self.x = self.parent.x

        x = self.x
        leading = 2
        y += leading / 2
        for child in self.children:
            child.layout(x, y)
            x += child.w + child.post_space_width
            self.h = max(self.h, child.h + leading)
        self.w = x - self.x

    # Returns this display list.
    def get_display_list(self):
        dl = []
        for child in self.children:
            dl.extend(child.get_display_list())
        return dl

    def get_height(self):
        return self.h


@dataclass
class InlineLayout:
    parent: BlockLayout or InputLayout
    node: TextNode or ElementNode
    children: List['LineLayout'] = field(default_factory=list)
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0

    def __post_init__(self):
        if type(self.parent) is not None:
            self.parent.children.append(self)
        if type(self.parent) is BlockLayout:
            self.x = self.parent.content_left()
            self.y = self.parent.content_top() + self.parent.h
        elif type(self.parent) is Page or type(self.parent) is InputLayout:
            self.x = self.parent.x
            self.y = self.parent.y
        LineLayout(self)

    def layout(self):
        self.w = self.parent.content_width()
        self.recurse(self.node)
        y = self.y
        for child in self.children:
            child.layout(y)
            y += child.h
        self.h = y - self.y

    # Lays out the argument node, and all of its descendants.
    def recurse(self, node):
        if isinstance(node, ElementNode) and node.tag in ['input', 'textarea', 'button']:
            self.input(node)
        elif isinstance(node, ElementNode):
            for child in node.children:
                self.recurse(child)
        else:
            self.text(node)

    def input(self, node):
        tl = InputLayout(node, multiline=(node.tag == 'textarea'))
        line = self.children[-1]
        if line.w + tl.w > self.w:
            line = LineLayout(self)
        tl.attach(line)

    # Lays out the provided text node within the x & y bounds of its parent.
    def text(self, node):
        # account for entry space if present
        if node.text[0].isspace() and len(self.children[-1].children) > 0:
            self.children[-1].children[-1].add_space()

        # populate display list
        words = node.text.split()
        for i, word in enumerate(words):
            tl = TextLayout(node, word)
            line = self.children[-1]
            if line.w + tl.w > self.w:
                line = LineLayout(self)
            tl.attach(line)
            if i != len(words) - 1 or node.text[-1].isspace():
                tl.add_space()

    # Returns the height of this.
    def get_height(self):
        return self.h

    # Returns this display list.
    def get_display_list(self):
        dl = []
        for child in self.children:
            dl.extend(child.get_display_list())
        return dl

    # Returns the font based on the bold and italic class variables.
    def get_font(self):
        fonts = {  # (bold, italic) -> font
            (False, False): tkinter.font.Font(family="Times", size=16),
            (True, False): tkinter.font.Font(family="Times", size=16, weight="bold"),
            (False, True): tkinter.font.Font(family="Times", size=16, slant="italic"),
            (True, True): tkinter.font.Font(family="Times", size=16, weight="bold", slant="italic"),
        }
        return fonts[self.node.style['font-weight'] == 'bold', self.node.style['font-style'] == 'italic']


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
    color: str
    font: tkinter.font.Font

    def draw(self, scroll_y, canvas):
        canvas.create_text(self.x, self.y - scroll_y, text=self.text, font=self.font, anchor='nw', fill=self.color)


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
        canvas.create_rectangle(self.x1, self.y1 - scroll_y, self.x2, self.y2 - scroll_y)


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

    def matches(self, node):
        clazz_match = node.attributes.get("class", "").split()
        if len(clazz_match) > 0:
            return self.clazz == clazz_match
        else:
            return False

    @staticmethod
    def score():
        return 16


@dataclass(frozen=True)
class IdSelector:
    id: str

    def matches(self, node):
        id_match = node.attributes.get("id", "").split()
        if len(id_match) > 0:
            return self.id == id_match[0]
        else:
            return False

    @staticmethod
    def score():
        return 256


@dataclass(frozen=True)
class PseudoclassSelector:
    clazz: str

    def matches(self, node):
        is_match = self.clazz in node.pseudoClasses
        return is_match

    @staticmethod
    def score():
        return 0


@dataclass
class Browser:
    window: tkinter.Tk = None
    canvas: tkinter.Canvas = None
    page: Page = None
    layout: BlockLayout = None
    history: [str] = None
    url: str = ''
    scroll_y: int = 0
    max_h: int = 0
    nodes: ElementNode = None
    rules: [] = None
    display_list: [] = None
    js: dukpy.JSInterpreter = None
    js_handles: {} = None
    timer: 'Timer' = None
    hovered_elt: ElementNode = None
    jar: {} = None

    def __post_init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(self.window, width=800, height=600)
        self.canvas.pack()
        self.window.bind("<Up>", self.scroll_up)
        self.window.bind("<Down>", self.scroll_down)
        self.window.bind("<Button-1>", self.handle_click)
        self.window.bind("<Motion>", self.handle_hover)
        self.history = []
        self.timer = Timer()
        self.js = dukpy.JSInterpreter()
        self.js_handles = {}
        self.jar = {}
        self.js.export_function("log", print)
        self.js.export_function("querySelectorAll", self.js_querySelectorAll)
        self.js.export_function("getAttribute", self.js_getAttribute)
        self.js.export_function("innerHTML", self.js_innerHTML)
        self.js.export_function("cookie", self.js_cookie)
        with open("runtime.js") as f:
            self.js.evaljs(f.read())

    def browse(self, init_input, is_html):
        self.timer.start('Downloading')
        body = None
        if is_html:
            body = init_input
        else:
            url = init_input
            self.history.append(url)
            self.url = url
            host, port, path, fragment = parse_url(url)
            # req_headers = {}
            # if len(self.jar.items()) > 0:
            #     cookie_string = ""
            #     for key, value in self.jar.items():
            #         cookie_string += "&" + key + "=" + value
            #     req_headers = {"Cookie": cookie_string[1:]}
            req_headers = {}
            cookies = self.jar.get((host, port), {})
            if len(cookies) > 0:
                req_headers = {"cookie": cookies}
            headers, body = request('GET', host, port, path, headers=req_headers)
            # if "set-cookie" in headers:
            #     kv, params = headers["set-cookie"].split(";")
            #     key, value = kv.split("=", 1)
            #     self.jar[key] = value
            if "set-cookie" in headers:
                kv = headers["set-cookie"]
                key, value = kv.split("=", 1)
                origin = (host, port)
                self.jar[origin] = value
            self.timer.stop()
        self.parse(body, False)

    def parse(self, body, inner_mode):
        self.timer.start('Parse HTML')
        text = lex(body)
        nodes = populate_tree(text)
        self.nodes = nodes
        self.rules = []
        self.timer.stop()
        self.timer.start('Parse CSS')
        with open("default.css") as f:
            r = parse_css(f.read())
            self.rules.extend(r)
        links = find_style_links(self.nodes)
        if links is not None and len(links) > 0:
            for link in links:
                l_host, l_port, l_path, l_fragment = parse_url(relative_url(link, self.url))
                header, body = request('GET', l_host, l_port, l_path)
                self.rules.extend(parse_css(body))
        self.rules.sort(key=lambda x: x[0].score())
        self.timer.stop()
        self.timer.start("Run JS")
        scripts = find_scripts(self.nodes, [])
        if scripts is not None and len(scripts) > 0:
            for script in scripts:
                l_host, l_port, l_path, l_fragment = \
                    parse_url(relative_url(script, self.url))
                header, body = request('GET', l_host, l_port, l_path)
                self.js.evaljs(body)
        self.timer.stop()
        self.re_layout()
        if inner_mode:
            return nodes

    def re_layout(self):
        self.timer.start('Style')
        apply_styles(self.nodes, self.rules)
        self.timer.stop()
        self.timer.start('Layout')
        self.page = None
        self.page = Page([])
        self.layout = BlockLayout(self.page, self.nodes)
        self.layout.layout()
        self.timer.stop()
        self.max_h = self.layout.get_height()
        self.timer.start('Display List')
        self.display_list = self.layout.get_display_list()
        self.timer.stop()
        self.timer.start('Rendering')
        self.render()
        self.timer.stop()

    def scroll_down(self, e):
        SCROLL_STEP = 100
        page_padding = 13
        window_height = 600
        max_h = self.layout.get_height()
        self.scroll_y = min(self.scroll_y + SCROLL_STEP, page_padding + max_h - window_height)
        self.render()

    def scroll_up(self, e):
        SCROLL_STEP = 100
        self.scroll_y = max(self.scroll_y - SCROLL_STEP, 0)
        self.render()

    def handle_click(self, e):
        if e.y < 60:  # Browser chrome
            if 10 <= e.x < 35 and 10 <= e.y < 50:
                self.go_back()
        else:
            x, y = e.x, e.y + self.scroll_y - 60
            elt = find_element(x, y, self.layout)
            while elt and not (isinstance(elt, ElementNode) and
                               (elt.tag == "a" and "href" in elt.attributes or elt.tag in ['input', 'textarea', 'button'])):
                elt = elt.parent
            if elt and not self.event('click', elt):
                if elt.tag == 'a':
                    url = relative_url(elt.attributes["href"], self.url)
                    self.browse(url, False)
                elif elt.tag == 'button':
                    self.submit_form(elt, elt.attributes)
                else:
                    self.edit_input(elt)

    def handle_hover(self, e):
        pass
        # # Remove any previous hovering
        # print('HOVER CALL')
        # if self.hovered_elt:
        #     print('Removing hover from element: ', self.hovered_elt.attributes['id'])
        #     self.hovered_elt.pseudoClasses.remove("hover")
        # self.hovered_elt = None
        #
        # # Find nearest box layout parent
        # x, y = e.x, e.y - 60 + self.scroll_y
        # elt = find_element(x, y, self.layout)
        # while elt and not isinstance(elt, ElementNode):
        #     elt = elt.parent
        #
        # # If we found our new element, add class
        # if elt and elt.tag != 'body':
        #     elt.pseudoClasses.add("hover")
        #     self.hovered_elt = elt
        #
        # self.re_layout()

    def edit_input(self, element):
        new_text = input('Enter new text: ')
        if element.tag == 'input':
            element.attributes["value"] = new_text
        else:
            element.children = [TextNode(new_text, element)]
        self.event("change", element)
        self.re_layout()

    def submit_form(self, element, elm_level_params):
        print('submitting form...')
        print('element is: ', element)
        # find form containing the button we clicked
        while element and element.tag != 'form':
            element = element.parent
            print('next element up: ', element.tag)
        if element and not self.event("submit", element):
            params = {}
            # if we have element level params, add those (use case: button has id attribute)
            if elm_level_params is not None and len(elm_level_params) > 0:
                for key in elm_level_params:
                    params[key] = elm_level_params[key]

            # compose dictionary of all form inputs
            inputs = find_inputs(element, [])
            num_inputs = 0
            for curr_input in inputs:
                if curr_input.tag == 'input':
                    id_param = curr_input.attributes.get("id", "")
                    if id_param == "":
                        id_param = 'input_{}'.format(num_inputs)
                        num_inputs += 1
                    params[id_param] = curr_input.attributes.get("value", "")
                else:
                    id_param = curr_input.attributes.get("id", "")
                    if id_param == "":
                        id_param = 'input_{}'.format(num_inputs)
                        num_inputs += 1
                    params[id_param] = curr_input.children[0].text if curr_input.children else ""
            self.post(relative_url(element.attributes["action"], self.history[-1]), params)

    def post(self, url, params):
        print('posting...')
        body = ''
        for param, value in params.items():
            body += '&' + param + '='
            body += value.replace(' ', '%20')
        body = body[1:]
        host, port, path, fragment = parse_url(url)

        req_headers = {}
        cookies = self.jar.get((host, port), {})
        if len(cookies) > 0:
            req_headers = {"cookie": cookies}
        print('performing post request to: ', host)
        headers, body = request('POST', host, port, path, req_headers, body)
        self.history.append(url)
        if "set-cookie" in headers:
            kv = headers["set-cookie"]
            key, value = kv.split("=", 1)
            origin = (host, port)
            self.jar[origin] = value
        self.parse(body, False)

    def render(self):
        self.canvas.delete("all")
        for cmd in self.display_list:
            cmd.draw(self.scroll_y - 60, self.canvas)
        self.canvas.create_rectangle(0, 0, 800, 60, fill='white')
        self.canvas.create_rectangle(10, 10, 35, 50)
        self.canvas.create_polygon(15, 30, 30, 15, 30, 45, fill='black')
        self.canvas.create_rectangle(40, 10, 790, 50)
        self.canvas.create_text(45, 15, anchor='nw', text=self.url)

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.browse(back, False)

    # JS Support
    def js_querySelectorAll(self, sel):
        selector, _ = css_selector(sel + "{", 0)
        elts = find_selected(self.nodes, selector, [])
        out = []
        for elt in elts:
            if elt.handle == 0:
                handle = len(self.js_handles) + 1
                elt.handle = handle
                self.js_handles[handle] = elt
                out.append(handle)
            else:
                out.append(elt.handle)
        return out

    def js_getAttribute(self, handle, attr):
        elt = self.js_handles[handle]
        return elt.attributes.get(attr, None)

    def js_innerHTML(self, handle, s):
        elt = self.js_handles[handle]
        new_html = "<newnode>{}</newnode>".format(s)
        new_node = self.parse(new_html, True)
        elt.children = new_node.children
        for child in elt.children:
            child.parent = elt
        self.re_layout()

    def js_cookie(self):
        host, port, path, fragment = parse_url(self.history[-1])
        cookies = self.jar.get((host, port), {})

        cookie_string = ""
        for key, value in cookies.items():
            cookie_string += "&" + key + "=" + value
        return cookie_string[1:]

    def event(self, eType, elt):
        cancelled = False
        if hasattr(elt, 'handle'):
            eval_string = "__runHandlers({}, \"{}\")".format(elt.handle, eType)
            cancelled = self.js.evaljs(eval_string)
            return cancelled
        else:
            print('Event has no handler', eType)
            return cancelled


@dataclass
class Timer:
    phase: str = None
    time: float = None

    def start(self, name):
        if self.phase:
            self.stop()
        self.phase = name
        self.time = time.time()

    def stop(self):
        # print("[{:>10.6f}] {}".format(time.time() - self.time, self.phase))
        self.phase = None


def find_selected(node, sel, out):
    if not isinstance(node, ElementNode):
        return
    if sel.matches(node):
        out.append(node)
    for child in node.children:
        find_selected(child, sel, out)
    return out


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
    elif s[i] == ":":
        name, i = css_value(s, i + 1)
        return PseudoclassSelector(name), i
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
    if not isinstance(node, TextNode) and 'id' in node.attributes:
        print('Trying to find rules for node: ', node.attributes['id'])

    if not isinstance(node, ElementNode):
        node.style = node.parent.style
        return

    # apply css styles
    for selector, pairs in rules:
        if selector.matches(node):
            print('found a style match for style: ', selector)
            if 'id' in node.attributes:
                print('node id is: ', node.attributes['id'])
            for prop in pairs:
                node.style[prop] = pairs[prop]
                if isinstance(selector, PseudoclassSelector):
                    print('Applying hover style to node: ', node.attributes['id'])

    # TODO: only inline styles are working?
    # apply inline styles
    for prop, value in node.compute_style().items():
        node.style[prop] = value
    # apply inherited styles
    INHERITED_PROPS = ['font-style', 'font-weight', 'color']
    for prop in INHERITED_PROPS:
        if prop not in node.style:
            if node.parent is None:
                if prop != 'color':
                    node.style[prop] = 'normal'
                else:
                    node.style[prop] = 'black'
            else:
                node.style[prop] = node.parent.style[prop]
    # recurse through children
    for child in node.children:
        apply_styles(child, rules)

# TODO: erase, depreciated...
# def get_browser_styles():
#     with open("default.css") as f:
#         browser_style = f.read()
#         browser_rules = parse_css(browser_style)
#         browser_rules.sort(key=lambda x: x[0].score())
#         return browser_rules


def find_style_links(node):
    listee = []
    if not isinstance(node, ElementNode):
        return
    if node.tag == "link" and \
            node.attributes.get("rel", "") == "stylesheet" and \
            "href" in node.attributes:
        listee.append(node.attributes["href"])
    for child in node.children:
        find_style_links(child)
    return listee


# Finds all inputs and buttons and grabs name or ID attributes from them
def find_inputs(element, out):
    if not isinstance(element, ElementNode):
        return
    if element.tag == 'input' or element.tag == 'textarea' and 'name' in element.attributes:
        out.append(element)
    for child in element.children:
        find_inputs(child, out)
    return out


def find_scripts(node, out):
    if not isinstance(node, ElementNode): return
    if node.tag == "script" and \
       "src" in node.attributes:
        out.append(node.attributes["src"])
    for child in node.children:
        find_scripts(child, out)
    return out


# Networking Stuff
# Parses the host, port, path, and fragment components of the provided url, if they exist.
# Reports an error if the argument does not start with http://
# Defaults to port 80 if none provided.
def parse_url(url):
    if url.startswith("http://"):
        url = url[len("http://"):]
    if url.startswith("https://"):
        url = url[len("https://"):]
    host_port, path_fragment = url.split("/", 1) if "/" in url else (url, "")
    host, port = host_port.rsplit(":", 1) if ":" in host_port else (host_port, "80")
    path, fragment = ("/" + path_fragment).rsplit("#", 1) if "#" in path_fragment else ("/" + path_fragment, None)
    return host, int(port), path, fragment


# Turn a relative url into an absolute one
def relative_url(url, current):
    if url.startswith('\''):
        url = strip_literals(url)
    if url.startswith('http://') or url.startswith('https://'):
        ret_url = url
        return ret_url
    elif url.startswith('/'):
        slash_split = current.split('/')
        if len(slash_split) > 1:
            base = slash_split[0]
            print('update relative url: ', base + url)
            return base + url
        else:
            ret_url = "/".join(current.split("/")[:3]) + url
            print('relative url: ', ret_url)
            return ret_url
    else:
        ret_url = current.rsplit("/", 1)[0] + "/" + url
        return ret_url


def strip_literals(string):
    return string[1: (len(string) - 1)]


# Returns the header and body responses obtained from the provided host and path arguments.
# Reports an error if anything but a 200/OK status obtained from the host.
def request(method, host, port, path, headers={}, body=None):
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    s.connect((host, port))
    s.send("{} {} HTTP/1.0\r\nHost: {}\r\n".format(method, path, host).encode("utf8"))
    for header, value in headers.items():
        s.send("{}: {}\r\n".format(header, value).encode("utf8"))
    if body:
        body = body.encode('utf8')
        s.send("Content-Length: {}\r\n\r\n".format(len(body)).encode("utf8"))
        s.send(body)
    else:
        s.send("\r\n".encode('utf8'))

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
# Ignores comments.
def lex(source):
    out = []
    text = ""
    in_comment = False
    for i in range(len(source)):
        c = source[i]
        # just finished text piece, append to list & reset
        if c == "<":
            if text:
                out.append(Text(text=text))
            text = ""
            if source[i+1] == '!':
                in_comment = True
        # just finished tag piece, append to list & reset
        elif c == ">":
            if text:
                out.append(Tag(tag=text, isClose=text.startswith("/")))
            text = ""
            in_comment = False
        elif not in_comment:
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
                if child.tag not in ["br", "link", "meta", "input"]:
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
                if node is None:
                    print(tag)

                elif node.parent is not None:
                    current_node = node.parent

    return current_node


def find_element(x, y, layout):
    for child in layout.children:
        result = find_element(x, y, child)
        if result:
            return result
    if layout.x <= x < layout.x + layout.w and \
            layout.y <= y < layout.y + layout.get_height():
        if hasattr(layout, 'node'):
            return layout.node


# Returns true if display style is set to inline
def is_inline(node):
    return (isinstance(node, TextNode) and not node.text.isspace()) or \
           node.style.get("display", "block") == "inline"


# Assumes we always have a valid Npx string as an argument
def strip_px(px):
    pieces = px.split("px")
    if len(pieces) > 0:
        return int(pieces[0])


# Run Stuff
def run():
    browser = Browser()
    if str(sys.argv[1]).startswith('http') or str(sys.argv[1]).startswith('127') or str(sys.argv[1]).startswith('local'):
        browser.browse(sys.argv[1], False)
    else:
        print("not a site, treating as raw html...")
        browser.browse(sys.argv[1], True)
    tkinter.mainloop()


if __name__ == "__main__":
    import sys
    run()
