$(document).ready(function() {

    dragdropok = true;

    function mod(n, m) {
        // https://stackoverflow.com/questions/4467539/
        // "JavaScript % (modulo) gives a negative result for negative numbers"
        return ((n % m) + m) % m;
    }

    function escapeHtml(text) {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function progress(evt) {
        if (evt.lengthComputable) {
            var percentComplete = evt.loaded / evt.total;
            //Do something with upload progress
            $("#progressbar").animate({
                width: percentComplete * 100 + "%"
            }, 250, function() {
                if (percentComplete == 1) { // reset Progressbar
                    $("#progressbar").css({
                        "opacity": "0"
                    });
                    $("#progressbar").css({
                        "width": "0%"
                    });
                    $("#progressbar").css({
                        "opacity": "1"
                    });
                }
            });
        }
    }

    ////////////////
    // Checkboxes //
    ////////////////

    $("#checkzsteg").click(function() {
        $(this).toggleClass("active");
        $("#allzsteg").attr("value",
            (1 + parseInt($("#allzsteg").attr("value"))) % 2);
    });
    $("#extractzsteg").click(function() {
        $(this).toggleClass("active");
        $("#zstegfiles").attr("value",
            (1 + parseInt($("#zstegfiles").attr("value"))) % 2);
    });

    $("#checkpasswd").click(function() {
        $(this).toggleClass("active");
        if ($(this).hasClass("active")) {
            $("#passwdsteg").fadeIn(300);
        } else {
            $("#passwdsteg").fadeOut(300);
        }
    });

    $("#filebut").click(function() {
        $("#fileup").click();
    });

    $("#fileup").change(function(event) {
        $("#txtbut").text(this.value.replace(/^.*[\\\/]/, ''));
    });

    $("#fileform").submit(function(e) {
        e.preventDefault();
        $("#backgroundprogressbar").show();
        $("#analyserbut").hide();
        $("#txtbut").html('File processing...<div class="loadinggif '
        + 'lds-rolling"><div></div></div>');
        $("#containerimg span").html('Waiting...<div class="loadinggif '
        + 'lds-rolling blackwait"><div></div></div>');
        $("#filebut").css("cursor", "auto");

        /*
            Post to /upload
            @fileup : Uploaded image (file)
        */
        var formData = new FormData($("form").get(0));
        $.ajax({
            type: 'POST',
            url: '/upload',
            data: formData,
            dataType: 'json',
            processData: false,
            contentType: false,
            complete: function(data) {
                askforfile(data.responseJSON); // Return json file
            }
        });
    });

    ///////////////////////////////
    // Format output and Regex   //
    ///////////////////////////////

    function formatCmd(data) {
        data = data.replace('\r\n', '\r');
        data = data.split('\r');
        data = data.filter(x => x != ''); // remove empty string
        data = data.filter(x => x.slice(-3) != '.. '); // remove empty string
        data = data.join('<br>');
        data = data.split('\n');
        data = data.join('<br>');
        data = data.replace(/<br><br>/g, "<br>");
        return data;
    }

    function fmExif(data) {
        data = data.replace(/---- /g, '<b>---- ');
        data = data.replace(/ ----/g, ' ----</b>');
        return data
    }

    function fmZsteg(data) {
        data = "<br>" + data;
        data = data.replace(/(<br>.*?\:)/g, '<b>$1</b>');
        return data
    }

    function fmBinwalk(data) {
        data = data.replace(/<br>(-*)<br>/g, '<br>');
        data = data.replace(/<br>([^ ]+) *([^ ]*) *([^\<]*)/g,
            '<tr><td>$1</td><td>$2</td><td>$3</td></tr>');
        data = "<table>" + data + "</table>";
        data = data.replace(/<br>/g, "");
        return data
    }

    //////////////////
    // Main handler //
    //////////////////

    function askforfile(data) {
        if ("Error" in data) {
            $("#txtbut").html(escapeHtml(data["Error"]));
            return false;
        }
        dragdropok = false;
        $("section").slideUp("fast", function() {
            $("#info").hide();
            $("#displayimg").show();
            $("section").css({
                "background-color": "transparent",
                "box-shadow": "inherit",
                "width": "100%"
            });

            //
            // Images display:
            //

            $.post("/process", {
                filename: data["File"]
            }, function(data) {

                if ("Error" in data) {
                    $('#out_imgs > div').append('<div>' + data["Error"] + '</div>');
                    $('#out_imgs span').slideUp(300, function(){
                        $('#out_imgs > div').slideDown();
                    });
                    return;
                }
                if ("Alpha" in data["Images"]) { // Reorder key
                    arr = ["Supperimposed", "Red", "Green", "Blue", "Alpha"];
                } else {
                    arr = ["Supperimposed", "Red", "Green", "Blue"];
                }
                $.each(arr, function() {
                    $('#out_imgs > div').append('<h2 class="h2scan" style="color:' +
                        this + '">' + this + '</h2>');
                    $.each(data["Images"][this], function() {
                        $('#out_imgs > div').append('<img class="imgscandisplay" ' +
                            'src="uploads/' + this + '" />');
                    });
                });

                $(".imgscandisplay").click(function() {
                    $(".imgscandisplay").removeClass("active");
                    $(this).addClass("active");
                    newappend = '<div id="displayimgfull"><a href="' +
                        $(this).attr("src") + '" download><img src="' +
                        $(this).attr("src") + '" /></a></div>';
                    $(newappend).hide().appendTo("body").fadeIn(300);

                    $(document).keyup(function(e) {
                        if (e.keyCode == 27) { // [Escape]
                            $(".imgscandisplay").removeClass("active");
                            $("#displayimgfull").fadeOut(300, function() {
                                $(this).remove();
                            });
                        }

                    });
                    $("#displayimgfull").click(function() {
                        $("#displayimgfull").fadeOut(300, function() {
                            $(this).remove();
                        });
                    }).children().click(function(e) {});
                });

                $('#out_imgs span').slideUp(300, function(){
                    $('#out_imgs > div').slideDown();
                });

            }, "json");

            //
            // Zsteg display:
            //

            $.post("/zsteg", {
                    filename: data["File"],
                    zstegfiles: $("#zstegfiles").val(),
                    allzsteg: $("#allzsteg").val()
                },
                function(data) {

                    if ("Error" in data || "Error" in data["Zsteg"]) {
                        if ("Error" in data){
                            $('#out_zsteg > div').append("<div id='sbloc_zsteg' class='sbloc'>" +
                            fmZsteg(formatCmd(escapeHtml(data["Error"]))) + "</div>");
                            $('#out_zsteg span').slideUp(300, function(){
                                $('#out_zsteg > div').slideDown();
                            });
                            return;
                        }
                        $('#out_zsteg > div').append("<div id='sbloc_zsteg' class='sbloc'>" +
                        fmZsteg(formatCmd(escapeHtml(data["Zsteg"]["Error"]))) + "</div>");
                        $('#out_zsteg span').slideUp(300, function(){
                            $('#out_zsteg > div').slideDown();
                        });
                        return;
                    }
                    $('#out_zsteg > div').append("<div id='sbloc_zsteg' class='sbloc'>" +
                        fmZsteg(formatCmd(escapeHtml(data["Zsteg"]["Output"]))) + "</div>");


                    if ("File" in data["Zsteg"]) {
                        $('#out_zsteg > div').append("<button class='butdwl' data-src='" +
                            data["Zsteg"]["File"] +
                            "' type='button'>Download files !</button>");
                    }

                    $("#out_zsteg .butdwl").click(function() {
                        window.open($(this).data("src"), "_blank");
                    });

                    $('#out_zsteg span').slideUp(300, function(){
                        $('#out_zsteg > div').slideDown();
                    });
                }, "json");


            //
            // Steghide display:
            //

            $.post("/steghide", {
                filename: data["File"],
                passwdsteg: $("#passwdsteg").val()
            }, function(data) {
                if ("Error" in data || "Error" in data["Steghide"]) {
                    if ("Error" in data){
                        $('#out_steghide > div').append("<div id='sbloc_steghide' " +
                        "class='sbloc'>" +
                        formatCmd(escapeHtml(data["Error"])) +
                        "</div>");
                        $('#out_steghide span').slideUp(300, function(){
                            $('#out_steghide > div').slideDown();
                        });
                        return;
                    }
                    $('#out_steghide > div').append("<div id='sbloc_steghide' " +
                    "class='sbloc'>" +
                    formatCmd(escapeHtml(data["Steghide"]["Error"])) +
                    "</div>");
                    $('#out_steghide span').slideUp(300, function(){
                        $('#out_steghide > div').slideDown();
                    });
                    return;
                }
                $('#out_steghide > div').append("<div id='sbloc_steghide' " +
                    "class='sbloc'>" +
                    formatCmd(escapeHtml(data["Steghide"]["Output"])) + "</div>");

                if ("File" in data["Steghide"]) {
                    $('#out_steghide > div').append("<button class='butdwl' data-src='" +
                        data["Steghide"]["File"] +
                        "' type='button'>Download files !</button>");
                }


                $("#out_steghide .butdwl").click(function() {
                    window.open($(this).data("src"), "_blank");
                });

                $('#out_steghide span').slideUp(300, function(){
                    $('#out_steghide > div').slideDown();
                });
            }, "json");

            //
            // Outguess display:
            //

            $.post("/outguess", {
                filename: data["File"],
                passwdsteg: $("#passwdsteg").val()
            }, function(data) {
                if ("Error" in data || "Error" in data["Outguess"]) {
                    if ("Error" in data){
                        $('#out_outguess > div').append("<div id='sbloc_outguess' " +
                        "class='sbloc'>" +
                        formatCmd(escapeHtml(data["Error"])) +
                        "</div>");
                        $('#out_outguess span').slideUp(300, function(){
                            $('#out_outguess > div').slideDown();
                        });
                        return;
                    }
                    $('#out_outguess > div').append("<div id='sbloc_outguess' " +
                    "class='sbloc'>" +
                    formatCmd(escapeHtml(data["Outguess"]["Error"])) +
                    "</div>");
                    $('#out_outguess span').slideUp(300, function(){
                        $('#out_outguess > div').slideDown();
                    });
                    return;
                }
                $('#out_outguess > div').append("<div id='sbloc_outguess' " +
                    "class='sbloc'>" +
                    formatCmd(escapeHtml(data["Outguess"]["Output"])) + "</div>");

                if ("File" in data["Outguess"]) {
                    $('#out_outguess > div').append("<button class='butdwl' data-src='" +
                        data["Outguess"]["File"] +
                        "' type='button'>Download files !</button>");
                }


                $("#out_outguess .butdwl").click(function() {
                    window.open($(this).data("src"), "_blank");
                });

                $('#out_outguess span').slideUp(300, function(){
                    $('#out_outguess > div').slideDown();
                });
            }, "json");

            //
            // Exiftool display:
            //


            $.post("/exiftool", {
                filename: data["File"]
            }, function(data) {
                if ("Error" in data) {
                    $('#out_exifs > div').append("<div id='sbloc_exiftool' " +
                    "class='sbloc'>" +
                    formatCmd(escapeHtml(data["Error"])) + "</div>");
                    $('#out_exifs span').slideUp(300, function(){
                        $('#out_exifs > div').slideDown();
                    });
                    return;
                }
                $('#out_exifs > div').append("<div id='sbloc_exiftool' " +
                    "class='sbloc'>" +
                    fmExif(formatCmd(escapeHtml(data["Exiftool"]))) + "</div>");

                $('#out_exifs span').slideUp(300, function(){
                    $('#out_exifs > div').slideDown();
                });
            }, "json");

            //
            // Binwalk display:
            //

            $.post("/binwalk", {
                filename: data["File"]
            }, function(data) {
                if ("Error" in data) {
                    $('#out_binwalk > div').append("<div id='sbloc_binwalk' " +
                    "class='sbloc'>" +
                    formatCmd(escapeHtml(data["Error"])) + "</div>");
                    $('#out_binwalk span').slideUp(300, function(){
                        $('#out_binwalk > div').slideDown();
                    });
                    return;
                }
                $('#out_binwalk > div').append("<div id='sbloc_binwalk' " +
                    "class='sbloc'>" +
                    fmBinwalk(formatCmd(escapeHtml(data["Binwalk"]["Output"]))) +
                    "</div>");

                if ("File" in data["Binwalk"]) {
                    $('#out_binwalk > div').append("<button class='butdwl' data-src='" +
                        data["Binwalk"]["File"] +
                        "' type='button'>Download files !</button>");
                }


                $("#out_binwalk .butdwl").click(function() {
                    window.open($(this).data("src"), "_blank");
                });

                $('#out_binwalk span').slideUp(300, function(){
                    $('#out_binwalk > div').slideDown();
                });
            }, "json");

            //
            // Foremost display:
            //

            $.post("/foremost", {
                filename: data["File"]
            }, function(data) {
                if ("Error" in data) {
                    $('#out_foremost > div').append("<div id='sbloc_foremost' " +
                    "class='sbloc'>" +
                    formatCmd(escapeHtml(data["Error"])) + "</div>");
                    $('#out_foremost span').slideUp(300, function(){
                        $('#out_foremost > div').slideDown();
                    });
                    return;
                }
                $('#out_foremost > div').append("<div id='sbloc_foremost' " +
                    "class='sbloc'>"+escapeHtml(data["Foremost"]["Output"]) +
                    "</div>");

                if ("File" in data["Foremost"]) {
                    $('#out_foremost > div').append("<button class='butdwl' data-src='" +
                        data["Foremost"]["File"] +
                        "' type='button'>Download files !</button>");
                }


                $("#out_foremost .butdwl").click(function() {
                    window.open($(this).data("src"), "_blank");
                });

                $('#out_foremost span').slideUp(300, function(){
                    $('#out_foremost > div').slideDown();
                });
            }, "json");


            //
            // Strings display:
            //

            $.post("/strings", {
                filename: data["File"]
            }, function(data) {
                if ("Error" in data) {
                    $('#out_strings > div').append("<div id='sbloc_strings' " +
                    "class='sbloc'>" +
                    formatCmd(escapeHtml(data["Error"])) + "</div>");
                    $('#out_strings span').slideUp(300, function(){
                        $('#out_strings > div').slideDown();
                    });
                    return;
                }
                $('#out_strings > div').append("<div id='sbloc_strings' " +
                    "class='sbloc'><textarea class='txtareastr'>" +
                    escapeHtml(data["Strings"]) + "</textarea></div>");

                $("section").delay(500).slideDown();

                // Download buttons

                $('#out_strings span').slideUp(300, function(){
                    $('#out_strings > div').slideDown();
                });
            }, "json");

            $("#containerimg").slideDown();
            $("section").slideDown();
        });
    }



    ///////////////////////////////
    // Images navigation support //
    ///////////////////////////////

    $(document).keyup(function(e) {
        if ($(".imgscandisplay.active").length) {
            if (e.keyCode == 37) { // [Left]
                e.preventDefault();
                $oldimg = $(".imgscandisplay.active");
                $newimg = $oldimg.prev('img.imgscandisplay');
                if ($newimg.attr("src") == undefined) {
                    $newimg = $oldimg.prev().prev('img.imgscandisplay');
                    if ($newimg.attr("src") == undefined) {
                        $newimg = $(".imgscandisplay").last();
                    }
                }
                $oldimg.removeClass("active");
                $newimg.addClass("active");
                $("#displayimgfull").html('<a href="' + $newimg.attr("src") +
                    '" download><img src="' + $newimg.attr("src") +
                    '" /></a></div>');
            }
            if (e.keyCode == 39) { // [Reft]
                e.preventDefault();
                $oldimg = $(".imgscandisplay.active");
                $newimg = $oldimg.next('img.imgscandisplay');
                if ($newimg.attr("src") == undefined) {
                    $newimg = $oldimg.next().next('img.imgscandisplay');
                    if ($newimg.attr("src") == undefined) {
                        $newimg = $(".imgscandisplay").first();
                    }
                }
                $oldimg.removeClass("active");
                $newimg.addClass("active");
                $("#displayimgfull").html('<a href="' + $newimg.attr("src") +
                    '" download><img src="' + $newimg.attr("src") +
                    '" /></a></div>');
            }
            if (e.keyCode == 38) { // [Up]
                e.preventDefault();
                $oldimg = $(".imgscandisplay.active");
                $val = 1 + mod((($oldimg.index() - 1) - 9),
                    (($oldimg.parent().children(".imgscandisplay").length / 8) * 9))
                $newimg = $oldimg.parent().children().eq($val);
                $oldimg.removeClass("active");
                $newimg.addClass("active");
                $("#displayimgfull").html('<a href="' + $newimg.attr("src") +
                    '" download><img src="' + $newimg.attr("src") +
                    '" /></a></div>');
            }
            if (e.keyCode == 40) { // [Down]
                e.preventDefault();
                $oldimg = $(".imgscandisplay.active");
                $val = 1 + ((($oldimg.index() - 1) + 9) %
                    (($oldimg.parent().children(".imgscandisplay").length / 8) * 9))
                $newimg = $oldimg.parent().children().eq($val);
                $oldimg.removeClass("active");
                $newimg.addClass("active");
                $("#displayimgfull").html('<a href="' + $newimg.attr("src") +
                    '" download><img src="' + $newimg.attr("src") +
                    '" /></a></div>');
            }
        }
    });
    window.addEventListener("keydown", function(e) {
        // [Space] and Arrow keys
        if ($(".imgscandisplay.active").length && [32, 37, 38, 39, 40].indexOf(e.keyCode) > -1) {
            e.preventDefault();
        }
    }, false);

    ////////////////////////////////////////////////////////////////////
    // Drag & Drop support, thx internet
    // @bryc https://stackoverflow.com/questions/28226021/
    // Entire page as a dropzone for drag and drop
    ////////////////////////////////////////////////////////////////////

    var lastTarget = null;

    function isFile(evt) {
        var dt = evt.dataTransfer;
        for (var i = 0; i < dt.types.length; i++) {
            if (dt.types[i] === "Files") {
                return true;
            }
        }
        return false;
    }

    window.addEventListener("dragenter", function(e) {
        if (isFile(e) && dragdropok) {
            lastTarget = e.target;
            document.querySelector("#dropzone").style.visibility = "";
            document.querySelector("#dropzone").style.opacity = 1;
            document.querySelector("#textnode").style.fontSize = "48px";
        }
    });

    window.addEventListener("dragleave", function(e) {
        e.preventDefault();
        if ((e.target === document || e.target === lastTarget) && dragdropok) {
            document.querySelector("#dropzone").style.visibility = "hidden";
            document.querySelector("#dropzone").style.opacity = 0;
            document.querySelector("#textnode").style.fontSize = "42px";
        }
    });

    window.addEventListener("dragover", function(e) {
        e.preventDefault();
    });

    window.addEventListener("drop", function(e) {
        e.preventDefault();
        document.querySelector("#dropzone").style.visibility = "hidden";
        document.querySelector("#dropzone").style.opacity = 0;
        document.querySelector("#textnode").style.fontSize = "42px";
        if (e.dataTransfer.files.length == 1 && dragdropok) {
            let fileInput = document.querySelector('#fileup');
            fileInput.files = e.dataTransfer.files;
            document.querySelector("#txtbut").innerHTML = escapeHtml(
                e.dataTransfer.files[0].name);
        }
    });
});
