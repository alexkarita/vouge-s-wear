from flask_wtf import FlaskForm
from wtforms import StringField, SelectField
from wtforms.validators import DataRequired, Length

class CheckoutForm(FlaskForm):
    customer_name = StringField('Full Name',
        validators=[DataRequired(message='Please enter your full name')])

    phone = StringField('Phone Number',
        validators=[
            DataRequired(message='Please enter your phone number'),
            Length(min=10, max=13, message='Enter a valid Kenyan phone number')
        ])

    delivery_address = StringField('Delivery Address',
        validators=[DataRequired(message='Please enter your delivery address')])

    county = SelectField('County', choices=[
        ('nairobi',  'Nairobi — KES 200'),
        ('mombasa',  'Mombasa — KES 400'),
        ('kisumu',   'Kisumu — KES 400'),
        ('nakuru',   'Nakuru — KES 400'),
        ('eldoret',  'Eldoret — KES 400'),
        ('thika',    'Thika — KES 400'),
        ('nyeri',    'Nyeri — KES 400'),
        ('machakos', 'Machakos — KES 400'),
        ('other',    'Other County — KES 400'),
    ])