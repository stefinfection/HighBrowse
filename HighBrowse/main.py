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
    text = ""   # Stores tag/text data - NOTE: this will break if tag contains CSS
    for c in source:
        # Just finished text piece, append to list
        if c == "<":
            if text:
                out.append(Text(text=text))
            text = ""
        # Just finished tag piece, append to list & reset
        elif c == ">":
            if text:
                out.append(Tag(tag=text))
            text = ""
        else:
            text += c
    return out


def layout(tokens):
    display_list = []

    # initialize fonts
    fonts = {  # (bold, italic) -> font
        (False, False): tkinter.font.Font(family="Times", size=16),
        (True, False): tkinter.font.Font(family="Times", size=16, weight="bold"),
        (False, True): tkinter.font.Font(family="Times", size=16, slant="italic"),
        (True, True): tkinter.font.Font(family="Times", size=16, weight="bold", slant="italic"),
    }

    # initialize coordinates
    x, y = 13, 13

    # initialize font
    bold_count, italic_count = 0, 0
    font = fonts[(bold_count > 0, italic_count > 0)]
    terminal_space = True

    for tok in tokens:
        if isinstance(tok, Text):

            # account for entry space if present
            if tok.text[0].isspace() and not terminal_space:
                x += font.measure(" ")

            # update font based on last tag state
            # print("bold is: {}", (bold_count > 0))
            font = fonts[(bold_count > 0, italic_count > 0)]

            # iterate through words on line
            words = tok.text.split()

            for i, word in enumerate(words):
                w = font.measure(word)
                if x + w >= 787:
                    y += font.metrics("linespace") * 1.2
                    x = 13
                display_list.append((x, y, word, font))

                # update x to include word width AND a space if we're not at the end of the line
                x += w + (0 if i == len(words) - 1 else font.measure(" "))

            # udpate x to include a whitespace if last char in line really is one
            terminal_space = tok.text[-1].isspace()
            if terminal_space and words:
                x += font.measure(" ")
        elif isinstance(tok, Tag):
            if tok.tag == "i":
                italic_count += 1
            elif tok.tag == "/i":
                italic_count -= 1
            elif tok.tag == "b":
                bold_count += 1
            elif tok.tag == "/b":
                bold_count -= 1
            elif tok.tag == "/p":
                terminal_space = True
                x = 13
                y += font.metrics('linespace') * 1.2 + 16

    return display_list


def show(text):
    window = tkinter.Tk()
    canvas = tkinter.Canvas(window, width=800, height=600)
    canvas.pack()

    SCROLL_STEP = 100
    scrolly = 0
    display_list = layout(text)

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
    show(text)

if __name__ == "__main__":
    import sys
    run(sys.argv[1])

