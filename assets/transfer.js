$(function() {
    success_alert = $('#importsuccessalert');
    error_alert = $('#importerroralert');

    $("#import-chall-button").click(function (e) {
        var form = $("#import-form")[0];
        var formData = new FormData(form);
    
        $.ajax({
            url: '/admin/yaml',
            data: formData,
            type: 'POST',
            cache: false,
            contentType: false,
            processData: false,
            success: function (resp) {
                if (resp.success) {
                    form.reset();
                    success_alert.show();
                } else {
                    error_alert.html(resp.errors);
                    error_alert.show();
                }
            },
            error: function (resp) {
                error_alert.html("Oops, something went wrong! Challenges cannot be automatically imported.");
                error_alert.show();
            }
        });
    });

    $("#tarfile").click(function (e) {
        success_alert.hide();
        error_alert.hide();
    });
});

