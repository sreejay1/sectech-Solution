# models.py
from odoo import models, fields
from odoo.addons.queue_job.job import job
import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    admin_emails = fields.Char(compute='_compute_admin_emails')

    def _compute_admin_emails(self):
        """Compute admin emails for notification."""
        admin_users = self.env['res.users'].search([('groups_id', '=', self.env.ref('base.group_system').id)])
        self.admin_emails = ','.join(user.partner_id.email for user in admin_users if user.partner_id.email)
    
    @job
    def send_order_confirmation_email(self):
        """Send order confirmation email to admin users."""
        try:
            template_id = self.env.ref('my_order_module.email_template_order')
            if template_id:
                template_id.sudo().send_mail(self.id, force_send=True)
                _logger.info("Email sent successfully for Order ID: %s", self.id)
            else:
                _logger.error("Email template not found.")
        except Exception as e:
            _logger.error("Error sending email in background: %s", str(e))
