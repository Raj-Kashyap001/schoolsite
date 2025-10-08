from django.contrib import admin

# Register your models here.
from front_cms.models import GalleryImage, CarouselImage, PopupImage

# Register your models here.
admin.site.register([GalleryImage, CarouselImage, PopupImage])
