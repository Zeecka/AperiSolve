$(document).ready(function () {

	function escapeHtml(text) {
		return text
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;")
			.replace(/'/g, "&#039;");
	}
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
	function fmZsteg(data) {
		data = "<br>" + data;
		data = data.replace(/(<br>.*?\:)/g, '<b>$1</b>');
		if (data.indexOf("<b><br>") == 0) {  // remove first line break
			data = data.slice(7);
			data = "<b>" + data;
		}
		return data;
	}
	function timestampPrint(d) {
		var date = new Date(d);
		var dateStr =
			("00" + date.getDate()).slice(-2) + "/" +
			("00" + (date.getMonth() + 1)).slice(-2) + "/" +
			date.getFullYear() + " " +
			("00" + date.getHours()).slice(-2) + ":" +
			("00" + date.getMinutes()).slice(-2) + ":" +
			("00" + date.getSeconds()).slice(-2);
		return dateStr;
	}


	// check if config exist, else redirect /
	md5 = $("#md5").val();
	if (!md5.match(/^[0-9A-Fa-f]{32}$/)) {  // if not md5, reload
		document.location = "/";
	}

	$.get({
		url: "/stats/" + md5 + '?' + (new Date()).getTime(), async: false, success: function (data) {
			window.upl_stats = data;
		}
	}).fail(function () {  // if config doesnt exist, reload
		document.location = "/";
	});

	upl_stats = window.upl_stats;
	console.dir(window.upl_stats);
	// Load from config to html


	function FileConvertSize(aSize) {
		aSize = Math.abs(parseInt(aSize, 10));
		var def = [[1, 'octets'], [1024, 'ko'], [1024 * 1024, 'Mo'], [1024 * 1024 * 1024, 'Go'], [1024 * 1024 * 1024 * 1024, 'To']];
		for (var i = 0; i < def.length; i++) {
			if (aSize < def[i][0]) return (aSize / def[i - 1][0]).toFixed(2) + ' ' + def[i - 1][1];
		}
	}
	var file_names = [];
	var v = upl_stats["names"];
	for (var i in v) {
		file_names.push("<span class='code'>" + escapeHtml(i) + "</span>");
	}

	$("#config_name").html(file_names.join(', '));
	$("#config_size").text(FileConvertSize(upl_stats["size"]));
	$("#config_date_first").text(timestampPrint(upl_stats["first_submit"] * 1000));
	$("#config_date_last").text(timestampPrint(upl_stats["last_submit"] * 1000));
	$("#config_count").text(upl_stats["total_submit"]);

	var file_pwds = [];
	var v = upl_stats["passwords"];
	for (var i in v) {
		file_pwds.push("<span class='code'>" + escapeHtml(i) + "</span>");
	}
	$("#config_pwds").html(file_pwds.join(', '));

	/* Load first image */

	(function main_img() {
		$.ajax({
			url: 'static/uploads/' + md5 + '/' + upl_stats["image"] + '?' + (new Date()).getTime(),
			statusCode: {
				200: function () {
					$("#main_img").attr('src', 'static/uploads/' + md5 + '/' + upl_stats["image"] + '?' + (new Date()).getTime());
				},
				404: function () {
					setTimeout(main_img, 5000);
				}
			}
		});
	})();

	/* Load view images */

	(function load_view() {
		$.ajax({
			url: '/stats/' + md5 + '?' + (new Date()).getTime(), success: function (data) {
				if (data["status"]["view"] == "finished") {
					$("#rgb_load").slideUp();
					$("#r_load").slideUp();
					$("#g_load").slideUp();
					$("#b_load").slideUp();
					for (i = 1; i <= 8; i++) {
						$("#img_rgb_" + i).attr('src', 'static/uploads/' + md5 + '/view/image_rgb_' + i + '.png');
						$("#img_r_" + i).attr('src', 'static/uploads/' + md5 + '/view/image_r_' + i + '.png');
						$("#img_g_" + i).attr('src', 'static/uploads/' + md5 + '/view/image_g_' + i + '.png');
						$("#img_b_" + i).attr('src', 'static/uploads/' + md5 + '/view/image_b_' + i + '.png');
						$.ajax({
							url: 'static/uploads/' + md5 + '/view/image_a_' + i + '.png', success: function (data) {
								if (i == 1) {
									$("#img_a_" + i).slideDown();
									$("#img_a_" + i + " + div").slideDown();
								}
								$("#img_a_" + i).attr('src', 'static/uploads/' + md5 + '/view/image_a_' + i + '.png');
								$("#img_a_" + i).slideDown();
							}
						});
					}
				} else {
					setTimeout(load_view, 5000);
				}
			}
		});
	})();

	/* Load zsteg */

	(function load_zsteg() {
		$.ajax({
			url: '/stats/' + md5 + '?' + (new Date()).getTime(), success: function (data) {
				if (data["status"]["zsteg"] == "finished") {
					$("#btn_zsteg").removeClass("disable");
					$("#btn_zsteg").click(function () {
						window.location.href = 'static/uploads/' + md5 + '/zsteg.7z';
					});
					$.ajax({
						url: 'static/uploads/' + md5 + '/zsteg.txt?' + (new Date()).getTime(), success: function (data) {
							$("#result_zsteg").html(fmZsteg(formatCmd(escapeHtml(data))));
						}
					});
				} else {
					setTimeout(load_zsteg, 5000);
				}
			}
		});
	})();

	/* Load steghide */

	(function load_steghide() {
		$.ajax({
			url: '/stats/' + md5 + '?' + (new Date()).getTime(), success: function (data) {
				if (data["status"]["steghide"] == "finished") {
					$("#btn_steghide").removeClass("disable");
					$("#btn_steghide").click(function () {
						window.location.href = 'static/uploads/' + md5 + '/steghide.7z';
					});
					$.ajax({
						url: 'static/uploads/' + md5 + '/steghide.txt', success: function (data) {
							$("#result_steghide").html(formatCmd(escapeHtml(data)));
						}
					});
				} else {
					setTimeout(load_steghide, 5000);
				}
			}
		});
	})();

	/* Load outguess */

	(function load_outguess() {
		$.ajax({
			url: '/stats/' + md5 + '?' + (new Date()).getTime(), success: function (data) {
				if (data["status"]["outguess"] == "finished") {
					$("#btn_outguess").removeClass("disable");
					$("#btn_outguess").click(function () {
						window.location.href = 'static/uploads/' + md5 + '/outguess.7z';
					});
					$.ajax({
						url: 'static/uploads/' + md5 + '/outguess.txt', success: function (data) {
							$("#result_outguess").html(formatCmd(escapeHtml(data)));
						}
					});
				} else {
					setTimeout(load_outguess, 5000);
				}
			}
		});
	})();

	/* Load exiftool */

	(function load_exiftool() {
		$.ajax({
			url: '/stats/' + md5 + '?' + (new Date()).getTime(), success: function (data) {
				if (data["status"]["exiftool"] == "finished") {
					$.ajax({
						url: 'static/uploads/' + md5 + '/exiftool.json', success: function (data) {
							data = data[0];
							delete data["SourceFile"];
							var output = "<table>";
							for (var k in data) {
								if (typeof (data[k]) == "object") {
									output += '<tr><td colspan=2><center class="h1exif">' + escapeHtml(k) + '</center></td></tr>';
									for (var l in data[k]) {
										output += '<tr><td><b>' + escapeHtml(l) + '</b></td>';
										output += '<td style="text-align: left;">' + escapeHtml(data[k][l].toString()) + '</td></tr>';
									}
								} else {
									output += '<tr><td><b>' + escapeHtml(k) + '</b></td>';
									output += '<td style="text-align: left;">' + escapeHtml(data[k]) + '</td></tr>';
								}
							}
							$("#result_exiftool").html(output);
						}
					});
				} else {
					setTimeout(load_exiftool, 5000);
				}
			}
		});
	})();

	/* Load binwalk */
	function fmBinwalk(data) {
		data = data.replace(/<br>(-*)<br>/g, '<br>');
		data = data.replace(/<br>([^ ]+) *([^ ]*) *([^\<]*)/g,
			'<tr><td>$1</td><td>$2</td><td>$3</td></tr>');
		data = "<table>" + data + "</table>";
		data = data.replace(/<br>/g, "");
		data = data.replace(/<td>DECIMAL<\/td>/g, "<th>DECIMAL<\/th>");
		data = data.replace(/<td>HEXADECIMAL<\/td>/g, "<th>HEXADECIMAL<\/th>");
		data = data.replace(/<td>DESCRIPTION<\/td>/g, "<th>DESCRIPTION<\/th>");
		return data
	}
	(function load_binwalk() {
		$.ajax({
			url: '/stats/' + md5 + '?' + (new Date()).getTime(), success: function (data) {
				if (data["status"]["binwalk"] == "finished") {
					$("#result_binwalk").removeClass("disable");
					$("#result_binwalk").click(function () {
						window.location.href = 'static/uploads/' + md5 + '/binwalk.7z';
					});
					$.ajax({
						url: 'static/uploads/' + md5 + '/binwalk.txt', success: function (data) {
							$("#binwalk_table").html(fmBinwalk(formatCmd(escapeHtml(data))));
						}
					});
				} else {
					setTimeout(load_binwalk, 5000);
				}
			}
		});
	})();

	/* Load foremost */

	(function load_foremost() {
		$.ajax({
			url: '/stats/' + md5 + '?' + (new Date()).getTime(), success: function (data) {
				if (data["status"]["foremost"] == "finished") {
					$("#result_foremost").removeClass("disable");
					$("#result_foremost").click(function () {
						window.location.href = 'static/uploads/' + md5 + '/foremost.7z';
					});
				} else {
					setTimeout(load_foremost, 5000);
				}
			}
		});
	})();

	/* Load strings */

	(function load_strings() {
		$.ajax({
			url: '/stats/' + md5 + '?' + (new Date()).getTime(), success: function (data) {
				if (data["status"]["strings"] == "finished") {
					$.ajax({
						url: 'static/uploads/' + md5 + '/strings.txt', success: function (data) {
							$("#result_strings").text(data);
						}
					});
				} else {
					setTimeout(load_strings, 5000);
				}
			}
		});
	})();



	$(".imgscandisplay").click(function () {
		$(".imgscandisplay").removeClass("active");
		$(this).addClass("active");
		newappend = '<div id="displayimgfull"><a href="' +
			$(this).attr("src") + '" download><img src="' +
			$(this).attr("src") + '" /></a></div>';
		$(newappend).hide().appendTo("body").fadeIn(300);

		$(document).keyup(function (e) {
			if (e.keyCode == 27) { // [Escape]
				$(".imgscandisplay").removeClass("active");
				$("#displayimgfull").fadeOut(300, function () {
					$(this).remove();
				});
			}

		});
		$("#displayimgfull").click(function () {
			$("#displayimgfull").fadeOut(300, function () {
				$(this).remove();
			});
		}).children().click(function (e) { });
	});


	/* Load pcrt 

	(function load_pcrt() {
		$.ajax({
			url: '/stats/' + md5 + '?' + (new Date()).getTime(), success: function (data) {
				if (data["status"]["pcrt"] == "finished") {
					$("#result_pcrt").removeClass("disable");
					$("#result_pcrt").click(function () {
						window.location.href = 'static/uploads/' + md5 + '/PCRT.7z';
					});
					$.ajax({
						url: 'static/uploads/' + md5 + '/pcrt.txt', success: function (data) {
							$("#result_pcrt_raw").html(formatCmd(escapeHtml(data)));
						}
					});
				} else {
					setTimeout(load_pcrt, 5000);
				}
			}
		});
	})();
	*/

	(function load_pngcheck() {
		$.ajax({
			url: '/stats/' + md5 + '?' + (new Date()).getTime(), success: function (data) {
				if (data["status"]["pngcheck"] == "finished") {
					$.ajax({
						url: 'static/uploads/' + md5 + '/pngcheck.txt?' + (new Date()).getTime(), success: function (data) {
							$("#result_pngcheck").html(fmZsteg(formatCmd(escapeHtml(data))));
						}
					});
				} else {
					setTimeout(load_pngcheck, 5000);
				}
			}
		});
	})();

});