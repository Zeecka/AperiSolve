$(document).ready(function () {
    $.get({
        url: "static/uploads/stats.json" + '?' + (new Date()).getTime(), async: false, success: function (data) {
            window.general_config_data = data;
            for (var md5 in general_config_data["images"]) {
                $.get({
                    url: "static/uploads/" + md5 + "/config.json" + '?' + (new Date()).getTime(), async: false, success: function (data) {
                        $("#show").append("<div><a href='/" + md5 + "'><img src='/static/uploads/" + md5 + "/" + data["image"] + "'/></a></div>");
                    }
                });
            }
        }
    });
});