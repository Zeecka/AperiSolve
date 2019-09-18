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
            $("#passwdsteghide").fadeIn(300);
        } else {
            $("#passwdsteghide").fadeOut(300);
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
        $("#txtbut").html('File processing...<div id="loadinggif" ' +
                          'class="lds-rolling"><div></div></div>');
        $("#filebut").css("cursor", "auto");

        /*
            Post to /process
            @fileup : Uploaded image (file)
            @allzsteg : Active --all option for zsteg (bool 1/0)
            @zstegfiles : Active --extract option for zsteg (bool 1/0)
            @passwdsteghide : Password for steghide
        */
        var formData = new FormData($("form").get(0));
        $.ajax({
            type: 'POST',
            url: '/process',
            data: formData,
            dataType: 'json',
            processData: false,
            contentType: false,
            complete: function(data) {
                askforfile(data.responseJSON);  // Return json file
            }
        });
    });

    function formatCmd(data) {
        data = data.replace('\r\n', '\r');
        data = data.split('\r');
        data = data.filter(x => x != '');  // remove empty string
        data = data.filter(x => x.slice(-3) != '.. ');  // remove empty string 
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
        data = data.replace(/<br>(-*)<br>/g,'<br>');
        console.dir(data);
        data = data.replace(/<br>([^ ]+) *([^ ]*) *([^\<]*)/g, '<tr><td>$1</td><td>$2</td><td>$3</td></tr>');
        console.dir(data);
        data = "<table>" + data + "</table>";
        data = data.replace(/<br>/g, "");
        console.dir(data);
        //console.dir(data);
        return data
    }

    function askforfile(data) {
        if ("Error" in data) {
            $("#txtbut").html(escapeHtml(data["Error"]));
            return false;
        }
        dragdropok = false;
        $("section").slideUp("fast", function() {
            $("#info").hide();
            $("section").css({
                "background-color": "transparent",
                "box-shadow": "inherit",
                "width": "100%"
            });


            //
            // Images display:
            //


            $('#containerimg').append("<h2 class='h2info'>View</h2>");
            if ("Alpha" in data["Images"]) { // Reorder key
                arr = ["Supperimposed", "Red", "Green", "Blue", "Alpha"];
            } else {
                arr = ["Supperimposed", "Red", "Green", "Blue"];
            }
            $.each(arr, function() {
                $('#containerimg').append('<h2 class="h2scan" style="color:' + 
                                           this + '">' + this + '</h2>');
                $.each(data["Images"][this], function() {
                    $('#containerimg').append('<img class="imgscandisplay" ' +
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
                    if (e.keyCode == 27) {  // [Escape]
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


            //
            // Zsteg display:
            //

            $('#containerimg').append("<h2 class='h2info'>Zsteg</h2>");
            $('#containerimg').append("<div id='sbloc_zsteg' class='sbloc'>" + 
            fmZsteg(formatCmd(escapeHtml(data["Zsteg"]["Output"]))) + "</div>");


            if ("File" in data["Zsteg"]) {
                $('#containerimg').append("<button class='butdwl' data-src='" + 
                data["Zsteg"]["File"] + 
                "' type='button'>Download files !</button>");
            }

            //
            // Steghide display:
            //

            $('#containerimg').append("<h2 class='h2info'>Steghide</h2>");
            $('#containerimg').append("<div id='sbloc_steghide' "+
            "class='sbloc'>" + 
            formatCmd(escapeHtml(data["Steghide"]["Output"])) + "</div>");
            
            if ("File" in data["Steghide"]) {
                $('#containerimg').append("<button class='butdwl' data-src='" + 
                data["Steghide"]["File"] + 
                "' type='button'>Download files !</button>");
            }

            //
            // Exiftools display:
            //

            $('#containerimg').append("<h2 class='h2info'>Exiftool</h2>");
            $('#containerimg').append("<div id='sbloc_exiftool' " +
            "class='sbloc'>" + 
            fmExif(formatCmd(escapeHtml(data["Exiftool"]))) + "</div>");

            //
            // Binwalk display:
            //

            $('#containerimg').append("<h2 class='h2info'>Binwalk</h2>");
            $('#containerimg').append("<div id='sbloc_strings' " +
            "class='sbloc'>" + 
            fmBinwalk(formatCmd(escapeHtml(data["Binwalk"]["Output"]))) + 
            "</div>");

            if ("File" in data["Binwalk"]) {
                $('#containerimg').append("<button class='butdwl' data-src='" + 
                data["Binwalk"]["File"] + 
                "' type='button'>Download files !</button>");
            }


            $("section").delay(500).slideDown();

            //
            // Strings display:
            //

            $('#containerimg').append("<h2 class='h2info'>Strings</h2>");
            $('#containerimg').append("<div id='sbloc_strings' " +
            "class='sbloc'><textarea id='txtareastr'>" + 
            escapeHtml(data["Strings"]) + "</textarea></div>");

            $("section").delay(500).slideDown();
            
            // Download buttons
            
            $(".butdwl").click(function() {
                window.open($(this).data("src"), "_blank");
            });
            
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
        if ($(".imgscandisplay.active").length && 
            [32, 37, 38, 39, 40].indexOf(e.keyCode) > -1) {
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
