from rest_framework import renderers
import json


class UserRenderer(renderers.JSONRenderer):
    charset = 'utf-8'
    
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response')
        if response.status_code >= 400:
            # Handle error responses
            response_data = {
                'status': 'error',
                'errors': data
            }
        else:
            # Handle success responses
            response_data = {
                'status': 'success',
                'data': data
            }
        
        return json.dumps(response_data)









# class UserRenderer(renderers.JSONRenderer):
#     charset = 'utf-8'
    
#     def render(self, data, accepted_media_type=None, renderer_context=None):
#         response = ''
        
#         if 'ErrorDetail' in str(data):
#             response = json.dumps({'errors': data})
#         else:
#             response = json.dumps({'data': data})
        
#         return response 
    
# class DriverRenderer(renderers.JSONRenderer):
#     charset = 'utf-8'
    
#     def render(self, data, accepted_media_type=None, renderer_context=None):
#         response = ''
        
#         if 'ErrorDetail' in str(data):
#             response = json.dumps({'errors': data})
#         else:
#             response = json.dumps({'data': data})
        
#         return response
    
# class PassengerRenderer(renderers.JSONRenderer):

#     charset = 'utf-8'
    
#     def render(self, data, accepted_media_type=None, renderer_context=None):
#         response = ''
        
#         if 'ErrorDetail' in str(data):
#             response = json.dumps({'errors': data})
#         else:
#             response = json.dumps({'data': data})
        
#         return response

# class TripRenderer(renderers.JSONRenderer):
    
#         charset = 'utf-8'
        
#         def render(self, data, accepted_media_type=None, renderer_context=None):
#             response = ''
            
#             if 'ErrorDetail' in str(data):
#                 response = json.dumps({'errors': data})
#             else:
#                 response = json.dumps({'data': data})
            
#             return response

# class TripRequestRenderer(renderers.JSONRenderer):
        
#             charset = 'utf-8'
            
#             def render(self, data, accepted_media_type=None, renderer_context=None):
#                 response = ''
                
#                 if 'ErrorDetail' in str(data):
#                     response = json.dumps({'errors': data})
#                 else:
#                     response = json.dumps({'data': data})
                
#                 return response

# class TripRequestResponseRenderer(renderers.JSONRenderer):

#     charset = 'utf-8'
    
#     def render(self, data, accepted_media_type=None, renderer_context=None):
#         response = ''
        
#         if 'ErrorDetail' in str(data):
#             response = json.dumps({'errors': data})
#         else:
#             response = json.dumps({'data': data})
        
#         return response

        