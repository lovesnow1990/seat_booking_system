# seat_booking_system_backend/utils.py

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError # 可能會捕捉到的數據庫完整性錯誤

def custom_exception_handler(exc, context):
    # 先呼叫 DRF 預設的異常處理器來獲取標準響應
    response = exception_handler(exc, context)

    # 如果 DRF 已經處理了異常並生成了響應 (例如驗證錯誤、Http404)
    if response is not None:
        custom_response_data = {
            'code': 'unknown_error',
            'message': 'An unexpected error occurred.',
            'details': {}
        }

        # 處理 DRF 內建的驗證錯誤 (ValidationError)
        if status.is_client_error(response.status_code): # 4xx 錯誤
            # 處理 ValidationError (400 Bad Request)
            if response.status_code == status.HTTP_400_BAD_REQUEST and isinstance(response.data, dict):
                custom_response_data['code'] = 'validation_error'
                custom_response_data['message'] = 'Input validation failed.'
                custom_response_data['details'] = response.data # 將驗證細節放入 details

            # 處理 Http404 (NotFound)
            elif response.status_code == status.HTTP_404_NOT_FOUND:
                custom_response_data['code'] = 'not_found'
                custom_response_data['message'] = response.data.get('detail', 'Resource not found.')
                custom_response_data['details'] = {} # 清空 details

            # 處理權限錯誤 (PermissionDenied - 403 Forbidden)
            elif response.status_code == status.HTTP_403_FORBIDDEN:
                custom_response_data['code'] = 'permission_denied'
                custom_response_data['message'] = response.data.get('detail', 'Permission denied.')
                custom_response_data['details'] = {}

            # 處理認證錯誤 (NotAuthenticated - 401 Unauthorized)
            elif response.status_code == status.HTTP_401_UNAUTHORIZED:
                custom_response_data['code'] = 'authentication_required'
                custom_response_data['message'] = response.data.get('detail', 'Authentication credentials were not provided.')
                custom_response_data['details'] = {}

            # 如果有其他 DRF 預設處理的 4xx 錯誤，也可以在這裡添加更多 if/elif
            else:
                custom_response_data['code'] = 'client_error'
                custom_response_data['message'] = response.data.get('detail', 'Client side error.')

        # 處理伺服器端錯誤 (5xx errors)
        elif status.is_server_error(response.status_code): # 5xx 錯誤
            custom_response_data['code'] = 'server_error'
            custom_response_data['message'] = response.data.get('detail', 'A server error occurred.')
            custom_response_data['details'] = {}

        response.data = custom_response_data # 將響應數據替換為我們自定義的格式
        return response

    # 如果 DRF 預設處理器沒有生成響應 (表示這是一個未被 DRF 處理的 Python 異常)
    # 我們需要自己處理這些未捕捉的異常，例如數據庫完整性錯誤
    if isinstance(exc, IntegrityError):
        # 這是您遇到的 "duplicate key value violates unique constraint" 錯誤的類型
        # 您需要更詳細地解析 IntegrityError 訊息以獲取具體細節
        # 但簡化處理，可以直接返回一個通用訊息
        return Response({
            'code': 'unique_constraint_violation',
            'message': 'A duplicate entry exists. Please check your input (e.g., seat already taken).',
            'details': {'error_message': str(exc)} # 可以在開發環境顯示詳細錯誤，生產環境隱藏
        }, status=status.HTTP_409_CONFLICT) # 409 Conflict 更適合重複資源的錯誤

    # 對於所有其他未被 DRF 或上述 if 塊處理的 Python 異常
    # 這是最後的防線，返回一個通用的伺服器錯誤
    return Response({
        'code': 'internal_server_error',
        'message': 'An unexpected internal server error occurred.',
        'details': {'error_message': str(exc) if settings.DEBUG else None} # DEBUG 模式下顯示錯誤訊息
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)