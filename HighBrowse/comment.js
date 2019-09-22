function lengthCheck() {
    if (input.getAttribute("value").length > 100) {
        document.querySelectorAll("#errors")[0].innerHTML = "Comment too long!"
    }
}
input = document.querySelectorAll("input")[0];
input.addEventListener("change", lengthCheck);