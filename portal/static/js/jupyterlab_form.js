$(document).ready(function () {
    $("#jupyterlab-form").on('keyup change', function () {
        $('#jupyterlab-form').validate();
        var valid = $('#jupyterlab-form').valid();
        $('button[type="submit"]').attr("disabled", !valid);
    });
    $('#notebook-name').on('keydown', function (e) {
        if (!/[a-zA-Z0-9._-]/.test(e.key)) {
            e.preventDefault();
            e.returnValue = false;
        }
    });
    $('#gpu-memory-info-icon').click(function () {
        $('#availableGPUs').modal('show');
    });
    $('#gpu-instances-info-icon').click(function () {
        $('#GPUinstances').modal('show');
    });
    $('#docker-image-info-icon').click(function () {
        $('#dockerImage').modal('show');
    });
});