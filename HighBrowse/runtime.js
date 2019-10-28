// Global variables
console = {
    log: function(x) { call_python("log", x); }
};
document = {
    querySelectorAll: function(s) {
        return call_python("querySelectorAll", s).map(function(h) {
            return new Node(h);
        });
    }
};

// Node stuff
function Node(handle) {
    this.handle = handle;
}
Node.prototype.getAttribute = function(attr) {
    return call_python("getAttribute", this.handle, attr);
};
Node.prototype.addEventListener = function(type, handler) {
    if (!LISTENERS[this.handle]) LISTENERS[this.handle] = {};
    var dict = LISTENERS[this.handle];
    if (!dict[type]) dict[type] = [];
    var list = dict[type];
    list.push(handler);
};

Object.defineProperty(Node.prototype, 'innerHTML', {
    set: function(s) {
        call_python("innerHTML", this.handle, s);
    }
});
Object.defineProperty(document, 'cookie', {
    get: function() {
        return call_python("cookie");
    }
});


// Event stuff
LISTENERS = {};
function Event() {
    this.cancelled = false;
}
Event.prototype.preventDefault = function() {
    this.cancelled = true;
};
function __runHandlers(handle, type) {
    if (!LISTENERS[handle]) LISTENERS[handle] = {};
    var dict = LISTENERS[handle];
    if (!dict[type])
        dict[type] = [];
    var list = dict[type];
    var evt = new Event();
    for (var i = 0; i < list.length; i++) {
        list[i]();
    }
    return evt.cancelled;
}