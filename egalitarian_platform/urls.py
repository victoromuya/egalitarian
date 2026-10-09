from django.contrib import admin
from django.urls import path, include

# NOTE: media is deliberately NOT served at MEDIA_URL. The only media files are
# certificate PDFs, which must go through the ownership-checking
# certificate_download view — a public /media/ route would make them
# fetchable by guessable URL.
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('courses/', include('courses.urls')),
    path('events/', include('events.urls')),
    path('accounts/', include('accounts.urls')),
    path('exams/', include('exams.urls')),
]
