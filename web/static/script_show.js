$(document).ready(function () {
    $.get({
        url: "/info", async: false, success: function (data) {
            d = {}
            data.forEach(function (item, index) {
                d[item["md5_full"]] = "/static/uploads/"+item["md5_full"]+"/"+item["image"];
            });

            $('[data-src!=""]').each(function( index ) {
                src = $(this).data("src")
                $(this).attr("src", d[src]);
            });
        }
    });
});