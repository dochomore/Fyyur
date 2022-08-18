import re
from wtforms.validators import ValidationError

class PhoneValidator(object):
    def __init__(self, message=None):
        if not message:
            message = u'phone number must be in (XXX-XXX-XXXX) format.'
        self.message = message

    def __call__(self, form, field):
        if not re.search(r"\d{3}[-]\d{3}[-]\d{4}$", field.data):
          raise ValidationError("Invalid phone number")