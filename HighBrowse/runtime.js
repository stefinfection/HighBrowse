/* STATICS */
INPUT_VAL = 1;
COOKIE_VAL = 2;
PLEDGE_LEVEL = dukpy['pledge'];

/* GLOBALS */
console = {
    log: function(x) { call_python("log", x); }
};
document = {
    querySelectorAll: function(selector) {
        var hasInputPledge = (PLEDGE_LEVEL & INPUT_VAL) >= INPUT_VAL;
        if (hasInputPledge) {
            return call_python("querySelectorAll", selector).map(function(h) {
                return new Node(h);
            });
        } else {
            console.log('The requesting script does not have permission to access elements ' + selector);
            return [];
        }
    },
    evaluate: function(x, n) {
        return call_python("evaluate", x, n).map(function(h) {
            return new Node(h);
        });
    }
};
Object.defineProperty(document, 'cookie', {
    get: function() {
        var hasCookiePledge = (PLEDGE_LEVEL & COOKIE_VAL) >= COOKIE_VAL;
        if (hasCookiePledge) {
            return call_python("cookie");
        } else {
            console.log('The requesting script does not have permission to access cookies');
            return '';
        }
    }
});

/* NODE */
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
    // Register event listener on browser side to coordinate interpreter
    call_python("registerListener", this.handle, PLEDGE_LEVEL);

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

/* EVENTS */
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

/* XML HTTP REQUESTS */
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
