$(function() {
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
            success: function (data) {
                form.reset();
                alert('success')
            },
            error: function (resp) {
                alert('error')
            }
        });
    });
});

