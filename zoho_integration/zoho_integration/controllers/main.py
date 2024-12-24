from odoo import http
from odoo.http import request
from odoo.exceptions import UserError
import pdb  # Import pdb

class ZohoProductSyncController(http.Controller):
        @http.route('/zoho/generate_access_token', type='json', auth='user', methods=['POST'], csrf=False)
        def generate_access_token(self, record_id):
            try:
                # Call the generate_access_token method from the model
                result = request.env['zoho.config'].generate_access_token(record_id)
                pdb.set_trace()
                return result
            except Exception as e:
                return {'status': 'error', 'message': str(e)}