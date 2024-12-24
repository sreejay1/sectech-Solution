$(document).ready(function () {
    var csrfToken = $('meta[name="csrf_token"]').attr('content');
    // Bind the click event to the Place Order button
    $('.btn-place-order').on('click', function (ev) {
        ev.preventDefault();
        
        // Perform an AJAX request to confirm the order
        $.ajax({
            url: '/shop/orderconfirmed',
            type: 'GET',
            headers: {
                'X-CSRF-TOKEN': csrfToken
            },
            success: function (data) {
                $('body').append(data); // Append the modal to the body
                $('#orderConfirmationModal').modal('show'); // Show the modal
            },
            error: function (xhr, status, error) {
                console.error("Error confirming order:", error);
                alert("There was an error confirming your order. Please try again.");
            }
        });
    });
});
