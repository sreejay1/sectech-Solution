from odoo import models, fields

class SyncProductWizard(models.TransientModel):
    _name = 'sync.product.wizard'
    _description = 'Product Sync Wizard'

    message = fields.Text(string="Message", readonly=True)
    details = fields.Text(string="Details", readonly=True)

    def action_close_popup(self):
        return {'type': 'ir.actions.act_window_close'}
