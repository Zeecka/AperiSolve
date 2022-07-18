$(document).ready(function () {


    // parallax
    (function() {
    // Add event listener
    document.addEventListener("mousemove", parallax);
    const elem = document.querySelector(".mouse1");
    const elem2 = document.querySelector(".mouse2");
    // Magic happens here
    function parallax(e) {
        let _w = window.innerWidth;
        let _h = window.innerHeight;
        let _mouseX = e.clientX;
        let _mouseY = e.clientY;
        let _x = `${((_mouseX / _w) * 4 - 10)}vw`;
        let _y = `${((_mouseY / _h) * 4 + 5)}vh`;
        let _x2 = `${((_mouseX / _w) * 2 - 10)}vw`;
        let _y2 = `${((_mouseY / _h) * 2 + 5)}vh`;
        elem.style.left = _x;
        elem.style.top = _y;
        elem2.style.left = _x2;
        elem2.style.top = _y2;
    }
  })();


  function copyToClipboard(text) {
    var sampleTextarea = document.createElement("textarea");
    document.body.appendChild(sampleTextarea);
    sampleTextarea.value = text; //save main text in it
    sampleTextarea.select(); //select textarea contenrs
    document.execCommand("copy");
    document.body.removeChild(sampleTextarea);
  }


  $(".command:has(.clipboard)").css("cursor", "pointer");
  $(".command:has('.clipboard')").click(function () {
    copyToClipboard($(this).children(".clipboard").data("value"));
    $("#copiedclipboard").fadeIn(300).fadeOut(600);
  })

  $("#cheatsheet h2").click(function () {
    copyToClipboard(document.location.href.split('#')[0]+"#"+$(this).attr('id'));
    $("#copiedclipboard").fadeIn(300).fadeOut(600);
  })

});