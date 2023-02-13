# -*- coding: utf-8 -*-
# from odoo import http


# class CustomSfcd(http.Controller):
#     @http.route('/custom_sfcd/custom_sfcd/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_sfcd/custom_sfcd/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_sfcd.listing', {
#             'root': '/custom_sfcd/custom_sfcd',
#             'objects': http.request.env['custom_sfcd.custom_sfcd'].search([]),
#         })

#     @http.route('/custom_sfcd/custom_sfcd/objects/<model("custom_sfcd.custom_sfcd"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_sfcd.object', {
#             'object': obj
#         })
