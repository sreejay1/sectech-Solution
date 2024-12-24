# controllers/main.py
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class MyOrderController(http.Controller):
    @http.route('/shop/orderconfirmed', type='http', auth="public", website=True)
    def order_placed(self, **kwargs):
        """Handle order confirmation and show confirmation modal."""
        try:
            # Get the current website
            website = request.env['website'].get_current_website()

            # Get the current order
            order = website.sale_get_order()

            # Check if order is found
            if not order:
                return request.redirect('/shop/payment')  # Redirect if order not found

            # Mark the order as confirmed
            order.sudo().action_confirm()

            # Log order details for debugging
            _logger.info("Order ID: %s", order.id)
            _logger.info("Order Amount Total: %s", order.amount_total)
            _logger.info("Order Name: %s", order.name)
            _logger.info("Shipping Address: %s", order.partner_shipping_id.contact_address)

            # Send email to admin users using the send_order_confirmation_email method
            if hasattr(order, 'send_order_confirmation_email'):
                _logger.info("Calling send_order_confirmation_email for Order ID: %s", order.id)
                order.send_order_confirmation_email()  # Send the email in background
            else:
                _logger.error("send_order_confirmation_email method not found for Order ID: %s", order.id)

            # Clear the session after order is confirmed
            request.website.sale_reset()

            # Render the order confirmation modal view and pass the order to the template
            response = request.render('my_order_module.order_confirmation_modal', {
                'sale_order': order,
                'website': website,
            })

            # Add CORS headers to the response (optional)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE, PUT'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

            return response

        except Exception as e:
            _logger.error("Error in order_placed: %s", str(e))
            response = request.render('my_order_module.order_confirmation_modal', {
                'sale_order': None,
                'website': website,
            })

            # Add CORS headers to the response
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE, PUT'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

            return response
