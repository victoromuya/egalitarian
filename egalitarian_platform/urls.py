from django.contrib import admin
from django.urls import path, include

# Media is deliberately not served publicly. Course materials and certificates
# must go through the enrollment- or ownership-checking download views.
urlpatterns = [
    path('secret-admin-page/', admin.site.urls),
    path('', include('core.urls')),
    path('courses/', include('courses.urls')),
    path('events/', include('events.urls')),
    path('accounts/', include('accounts.urls')),
    path('exams/', include('exams.urls')),
]
