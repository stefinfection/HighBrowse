// Global variables
console = {
    log: function(x) { call_python("log", x); }
};
document = {
    querySelectorAll: function(selector, src) {
        var pledgeIdx = REQ_PLEDGE.indexOf(selector);
        var requiresPledge = pledgeIdx >= 0;
        if (!requiresPledge || (requiresPledge && hasPledge(selector, src))) {
            return call_python("querySelectorAll", selector).map(function(h) {
                return new Node(h);
            });
        } else {
            console.log('The script ' + src + ' does not have permission to access elements ' + selector);
            return [];
        }
    },
    evaluate: function(x, n) {
        return call_python("evaluate", x, n).map(function(h) {
            return new Node(h);
        });
    }
};

// Pledge stuff
REQ_PLEDGE = ['cookie', 'input'];
function hasPledge(type, src) {
    var hasPledge = call_python("getPledge", type, src);
    console.log('returning from getting pledge');
    return hasPledge;
}

// Node stuff
function Node(handle) {
    this.handle = handle;
}
Node.prototype.getAttribute = function(attr) {
    return call_python("getAttribute", this.handle, attr);
};
Node.prototype.setAttribute = function(attr, value) {
    return call_python("setAttribute", this.handle, attr, value);
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
Object.defineProperty(Node.prototype, 'textContent', {
    get: function() {
        return call_python("textContent", this.handle);
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

// HTTP Request stuff
function XmlHttpRequest() {
    this.url = '';
    this.reqType = '';
    this.headers = [];
}
XmlHttpRequest.prototype.open = function(reqType, url) {
    this.url = url;
    this.reqType = reqType;
};
XmlHttpRequest.prototype.setRequestHeader = function(name, value) {
    this.headers[name] = value;
};
XmlHttpRequest.prototype.send = function(params) {
    if (this.reqType === 'POST') {
        call_python("sendPost", this.url, params, this.headers, true);
    } else {
        console.log("Request type {} not yet supported".format(this.reqType));
    }
};
