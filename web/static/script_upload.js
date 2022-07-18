// File Upload
// 
$("#file-drag").click(function () {
  $("#file-upload").click();
});
$("#optionsform button").click(function () {
  $(this).toggleClass("disable");
  if ($(this).hasClass("disable")) {
    $(this).text($(this).data("disable"));
  } else {
    $(this).text($(this).data("enable"));
  }
});
function initFileUpl() {
  var fileSelect = document.getElementById('file-upload'),
    fileDrag = document.getElementById('file-drag'),
    submitButton = document.getElementById('submit-button');
  if (fileSelect) {
    fileSelect.addEventListener('change', fileInputSelectHandler, false);
  }

  // Is XHR2 available?
  var xhr = new XMLHttpRequest();
  if (fileDrag && xhr.upload) {
    // File Drop
    fileDrag.addEventListener('dragover', fileDragHover, false);
    fileDrag.addEventListener('dragleave', fileDragHover, false);
    fileDrag.addEventListener('drop', fileSelectHandler, false);
  }
}

function fileDragHover(e) {
  var fileDrag = document.getElementById('file-drag');

  e.stopPropagation();
  e.preventDefault();

  fileDrag.className = (e.type === 'dragover' ? 'hover' : 'modal-body file-upload');
}

function fileSelectHandler(e) {
  // Fetch FileList object
  var files = e.target.files || e.dataTransfer.files;

  // Cancel event and hover styling
  fileDragHover(e);
  // Process all File objects
  for (var i = 0, f; f = files[i]; i++) {
    parseFile(f);
  }
  var fileinput = document.getElementById('file-upload');
  fileinput.files = files;
}

function fileInputSelectHandler(e) {
  var files = e.target.files || e.dataTransfer.files;
  for (var i = 0, f; f = files[i]; i++) {
    parseFile(f);
  }
}
// Output
function output(msg) {
  // Response
  var m = document.getElementById('messages');
  m.innerHTML = msg;
}

function parseFile(file) {
  output(
    '<strong>' + encodeURI(file.name) + '</strong>'
  );

  // var fileType = file.type;
  // console.log(fileType);
  var imageName = file.name;

  var isGood = (/\.(?=jpeg|png|bmp|gif|tiff|jpg|jfif|jpe|tif)/gi).test(imageName);
  if (isGood) {
    document.getElementById('start').classList.add("hidden");
    document.getElementById('response').classList.remove("hidden");
    document.getElementById('notimage').classList.add("hidden");
    // Thumbnail Preview
    document.getElementById('file-image').classList.remove("hidden");
    document.getElementById('file-image').src = URL.createObjectURL(file);
  }
  else {
    document.getElementById('file-image').classList.add("hidden");
    document.getElementById('notimage').classList.remove("hidden");
    document.getElementById('start').classList.remove("hidden");
    document.getElementById('response').classList.add("hidden");
    document.getElementById("file-upload-form").reset();
  }
}

function setProgressMaxValue(e) {
  var pBar = document.getElementById('file-progress');

  if (e.lengthComputable) {
    pBar.max = e.total;
  }
}

function updateFileProgress(e) {
  var pBar = document.getElementById('file-progress');

  if (e.lengthComputable) {
    pBar.value = e.loaded;
  }
}

function uploadFile(file) {
  var xhr = new XMLHttpRequest(),
    fileInput = document.getElementById('class-roster-file'),
    pBar = document.getElementById('file-progress');
  if (xhr.upload) {
    // Progress bar
    pBar.style.display = 'inline';
    xhr.upload.addEventListener('loadstart', setProgressMaxValue, false);
    xhr.upload.addEventListener('progress', updateFileProgress, false);

    // File received / failed
    xhr.onreadystatechange = function (e) {
      if (xhr.readyState == 4) {  // when upload is ok
        response = JSON.parse(xhr.response);
        if ("File" in response) {
          document.location = "/" + response['File'];
        }
        else if ("Error" in response) {
          $("#error").text(response["Error"]);
          $("#error").slideDown();
        }
      }
    };

    // Start upload
    xhr.open('POST', '/upload', true);
    //xhr.setRequestHeader('Content-Type', 'multipart/form-data');
    var formData = new FormData();
    formData.append("file", file);
    formData.append("zsteg_ext", !$("#btn_zsteg_ext").hasClass("disable"));
    formData.append("zsteg_all", !$("#btn_zsteg_all").hasClass("disable"));
    formData.append("use_password", !$("#btn_password").hasClass("disable"));
    formData.append("password", $("input[name=password]").val());
    xhr.send(formData);
  }
}

// Check for the various File API support.
if (window.File && window.FileList && window.FileReader) {
  initFileUpl();
} else {
  document.getElementById('file-drag').style.display = 'none';
}

$("#upload_button").click(function () {
  //alert("ok");
  uploadFile($("#file-upload").prop('files')[0]);
});

$("#btn_password").click(function () {
  $("#password").slideToggle();
});
