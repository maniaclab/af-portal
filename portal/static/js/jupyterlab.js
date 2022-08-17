$(document).ready(function() {

    var updateStatus = function(tr, interval) {
      var counter = 0;
      var id = setInterval(function() {
        var notebook = tr.data("notebook");
        $.get("/jupyter/status/" + notebook, function(resp) {
          if (++counter > 30) {
            clearInterval(id);
          }
          else if (tr.data("status") == "Removed") {
            return;
          }
          else if (resp["status"] == "Not found") {
            clearInterval(id);
            tr.remove();
            if (tr.siblings().length == 0) {
              $(".table").remove();
              $(".container").append("<p>You currently have no notebooks.</p>");
            }
            tr.data("status", "Removed");
          }
          else if (resp["status"] == "Ready") {
            clearInterval(id);
            var url = tr.data('url');
            tr.children(".notebook-name").html("<a href='" + url + "' class='text-decoration-none' target='_blank'>" + notebook + "</a>");
          }
          tr.children(".notebook-status").html(resp["status"]);
        }); 
      }, interval);
    }

    $('.notebook-status').each(function() {
        var status = $(this).val();
        if (status != "Ready") {
          var tr = $(this).parent();
          updateStatus(tr, 5000);
        }
    }); 

    $('.notebook-remove a').on('click', function() {
      var td = $(this).parent();
      var tr = $(td).parent();
      var notebook = $(tr).data("notebook");
      $.get("/jupyter/remove/" + notebook, function(resp) {
        if (resp["success"]) {
          tr.children(".notebook-status").html("Removing notebook...");
          tr.children(".notebook-name").html(notebook);
          td.html("<i class='fa-regular fa-trash-can'></i>");
          updateStatus(tr, 10000);
        }
      });
    });
});