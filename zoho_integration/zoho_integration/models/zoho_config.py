from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta, datetime
import requests # type: ignore
import json
import http.client
import pdb  # Import pdb

class ZohoConfig(models.Model):
    _name = 'zoho.config'
    _description = 'Zoho Configuration'

    client_id = fields.Char('Client ID', required=True)
    client_secret = fields.Char('Client Secret', required=True)
    redirect_uri = fields.Char('Redirect URI')
    access_token = fields.Char('Access Token')
    refresh_token = fields.Char('Refresh Token')
    code = fields.Char('Code')
    grant_type = fields.Char('Grant Type')
    token_expires_at = fields.Datetime('Token Expires At', readonly=True)
    last_synced = fields.Datetime('Last Synced', readonly=True)
    access_token_expiration_date = fields.Datetime('Access Token Expiration Date', readonly=True)
    product_last_synced = fields.Datetime('Product Last Synced', readonly=True)
    organization_id = fields.Char('Organization ID')
    is_active = fields.Boolean(string="Active", default=False)
    
    @api.model
    def generate_access_token(self, record_id):
        # Fetch the record using the provided record_id
        record = self.browse(record_id)
        if not record:
            raise UserError("No record found to generate access token.")

        # URL for Zoho OAuth2 token exchange
        url = "https://accounts.zoho.com/oauth/v2/token"
        
        # Parameters to be sent for token generation
        params = {
            'code': record.code,
            'client_id': record.client_id,
            'client_secret': record.client_secret,
            'redirect_uri': record.redirect_uri,
            'grant_type': 'authorization_code',
        }

        # Make the POST request to Zoho API
        response = requests.post(url, data=params)

        # Handle the response
        if response.status_code == 200:
            token_data = response.json()
            
            # Extract the access_token, refresh_token, and expires_in from the response
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            expires_in = token_data.get('expires_in')  # Expiration time in seconds
            if access_token and refresh_token:
               # Save tokens and expiration time
                record.access_token = access_token
                record.refresh_token = refresh_token
                record.token_expires_at = fields.Datetime.now() + timedelta(seconds=expires_in)
                record.access_token_expiration_date = record.token_expires_at  # Set expiration date
                record.last_synced = fields.Datetime.now()

                return {'status': 'success', 'access_token': access_token, 'refresh_token': refresh_token}

            else:
                raise UserError("Failed to retrieve access token and refresh token from Zoho.")
        else:
            raise UserError(f"Failed to obtain tokens: {response.text}")

    def sync_products(self):
        if not self.access_token:
            raise UserError("Please authorize first to enable product synchronization.")

        if not self.organization_id:
            raise UserError("Organization ID is missing. Product synchronization cannot proceed.")

        if not self.is_active:
            raise UserError("This configuration is not active. Please activate it to enable product synchronization.")

        self.check_and_refresh_token(self.id)

        conn = http.client.HTTPSConnection("www.zohoapis.com")
        headers = {'Authorization': f"Zoho-oauthtoken {self.access_token}"}
        page = 1
        per_page = 200  # Fetch up to 200 items per API call
        all_items = []  # Collect all fetched products

        try:
            while True:
                # Fetch products in batches
                conn.request(
                    "GET", 
                    f"/inventory/v1/items?organization_id={self.organization_id}&page={page}&per_page={per_page}", 
                    headers=headers
                )
                res = conn.getresponse()

                if res.status == 401:
                    # Refresh token and retry
                    self.refresh_access_token()
                    headers['Authorization'] = f"Zoho-oauthtoken {self.access_token}"
                    conn.request(
                        "GET", 
                        f"/inventory/v1/items?organization_id={self.organization_id}&page={page}&per_page={per_page}", 
                        headers=headers
                    )
                    res = conn.getresponse()

                if res.status != 200:
                    raise UserError("Invalid Organization ID or unable to fetch items. Please check and try again.")

                data = res.read()
                response_json = json.loads(data.decode("utf-8"))
                items = response_json.get('items', [])

                if not items:
                    break  # Exit the loop when no more items are returned

                all_items.extend(items)
                page += 1

            # Batch process products
            ProductTemplate = self.env['product.template']
            ProductPublicCategory = self.env['product.public.category']
            ProductTag = self.env['product.tag']

            # Pre-fetch all categories and tags to minimize queries
            existing_categories = {
                cat.name: cat for cat in ProductPublicCategory.search([])
            }
            existing_tags = {
                tag.name: tag for tag in ProductTag.search([])
            }
            existing_products = {
                prod.name: prod for prod in ProductTemplate.search([])
            }

            to_create = []  # List to batch create products
            to_update = []  # List to batch update products

            for item in all_items:
                product_name = item.get('name')
                category_name = item.get('category_name', '').strip() or 'Uncategorized'
                manufacturer_name = item.get('manufacturer', '').strip() or 'No Manufacturer'
                available_stock = float(item.get('available_stock', 0))

                # Get or create the category
                category = existing_categories.get(category_name)
                if not category:
                    category = ProductPublicCategory.create({'name': category_name})
                    existing_categories[category_name] = category

                # Get or create the manufacturer tag
                manufacturer_tag = existing_tags.get(manufacturer_name)
                if not manufacturer_tag:
                    manufacturer_tag = ProductTag.create({'name': manufacturer_name})
                    existing_tags[manufacturer_name] = manufacturer_tag

                # Check if the product exists
                existing_product = existing_products.get(product_name)
                if existing_product:
                    to_update.append((existing_product, {
                        'public_categ_ids': [(4, category.id)],
                        'product_tag_ids': [(4, manufacturer_tag.id)],
                    }))
                else:
                    to_create.append({
                        'name': product_name,
                        'list_price': item.get('rate'),
                        'default_code': item.get('sku'),
                        'website_ribbon_id': 5 if available_stock == 0.0 else False,
                        'description_ecommerce': item.get('description'),
                        'is_published': True,
                        'public_categ_ids': [(6, 0, [category.id])],
                        'product_tag_ids': [(6, 0, [manufacturer_tag.id])],
                    })

            # Batch create and update products
            if to_create:
                ProductTemplate.create(to_create)
            for product, values in to_update:
                product.write(values)

            self.product_last_synced = fields.Datetime.now()

            return {
                'type': 'ir.actions.act_window',
                'name': 'Success',
                'res_model': 'sync.product.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_message': 'Products synchronized successfully!',
                    'default_details': f'Total products synced: {len(all_items)}',
                    'form_view_initial_mode': 'readonly'
                },
            }

        except Exception as e:
            raise UserError(f"Failed to sync products: {str(e)}")


    # Refresh Token
    def refresh_access_token(self):
        conn = http.client.HTTPSConnection("accounts.zoho.com")
        
        # The data required for refreshing the access token
        payload = f"grant_type=refresh_token&refresh_token={self.refresh_token}&client_id={self.client_id}&client_secret={self.client_secret}"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        try:
            # Send the request to refresh the token
            conn.request("POST", "/oauth/v2/token", payload, headers)
            res = conn.getresponse()
            
            if res.status != 200:
                raise UserError("Failed to refresh access token. Please check your refresh token or authorization details.")

            # Parse the response to get the new access token
            data = res.read()
            response_json = json.loads(data.decode("utf-8"))
            new_access_token = response_json.get('access_token')

            if not new_access_token:
                raise UserError("Access token refresh failed. No access token received.")
            
            # Update the access token
            self.access_token = new_access_token
            self.product_last_synced = fields.Datetime.now()  # Update last synced time
            
        except Exception as e:
            raise UserError(f"Error refreshing access token: {str(e)}")
    
    @api.constrains('is_active')
    def _check_unique_active(self):
        if self.is_active:
            active_records = self.search_count([('is_active', '=', True)])
            if active_records > 1:
                raise UserError("Only one Zoho Configuration entry can be active at a time.")
    @api.model
    def check_and_refresh_token(self, record_id):
        record = self.browse(record_id)
        if not record.refresh_token:
            raise UserError("Refresh token is missing. Cannot refresh access token.")

        # Use the refresh token to get a new access token from Zoho
        conn = http.client.HTTPSConnection("accounts.zoho.com")
        
        payload = f"grant_type=refresh_token&refresh_token={record.refresh_token}&client_id={record.client_id}&client_secret={record.client_secret}"
        headers = { 'Content-Type': 'application/x-www-form-urlencoded' }

        try:
            # Send the request to refresh the token
            conn.request("POST", "/oauth/v2/token", payload, headers)
            res = conn.getresponse()
            
            if res.status != 200:
                raise UserError("Failed to refresh access token. Please check your refresh token or authorization details.")
            
            data = res.read()
            response_json = json.loads(data.decode("utf-8"))
            new_access_token = response_json.get('access_token')
            
            if not new_access_token:
                raise UserError("Access token refresh failed. No access token received.")
            
            # Update the record with the new access token
            record.access_token = new_access_token

        except Exception as e:
            raise UserError(f"Error refreshing access token: {str(e)}")