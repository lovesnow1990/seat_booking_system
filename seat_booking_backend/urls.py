# seat_booking_system_backend/urls.py

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from booking import views

# 引入 drf_spectacular 的視圖
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# 創建一個路由器實例
router = DefaultRouter()
# 註冊您的視圖集到路由器
router.register(r'venues', views.VenueViewSet)
router.register(r'events', views.EventViewSet)
router.register(r'seats', views.SeatViewSet)
router.register(r'orders', views.OrderViewSet, basename='order')

urlpatterns = [
    path('admin/', admin.site.urls),
    # 將 DRF 的路由包含進來，API 的根路徑是 /api/
    path('api/', include(router.urls)),
    # 也可以添加 DRF 的登入/登出 URL，方便瀏覽器 API 測試
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    
    # === API 文檔相關 URL ===
    # 為您的 API 生成 OpenAPI schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'), 
    # 提供 Swagger UI 介面
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # 提供 Redoc 介面 (另一種美觀的文檔風格)
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]