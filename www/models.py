from __future__ import unicode_literals

# common
import uuid

# other
from jsonfield import JSONField

# django
from django.db import models
from django.utils import timezone


###############################################################################
# BaseModel
###############################################################################
class BaseModel(models.Model):
    add_date = models.DateTimeField(verbose_name="Add date", editable=False,
                                    db_index=True, default=timezone.now())
    update_date = models.DateTimeField(verbose_name="Update date",
                                       editable=False, default=timezone.now())

    class Meta(object):
        abstract = True

    def save(self, *args, **kwargs):
        # update dates
        if not self.id:
            self.add_date = timezone.now()
        self.update_date = timezone.now()

        self.on_before_save()
        result = super(BaseModel, self).save(*args, **kwargs)
        self.on_after_save()

        return result

    def on_before_save(self):
        pass

    def on_after_save(self):
        pass

    @property
    def class_name(self):
        return self.__class__.__name__.lower()


class Token(BaseModel):
    token = models.TextField(unique=True)

    def on_before_save(self):
        if not self.token:
            self.token = uuid.uuid4()

    def dict(self):
        return {
            'id': self.id,
            'authToken': self.token,
        }


class Track(BaseModel):
    points = JSONField()

    def dict(self):
        return {
            'id': self.id,
            'points': self.points,
        }


