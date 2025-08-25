from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TelField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Regexp


class CallbackForm(FlaskForm):
    """Класс формы для обратного звонка."""
    name = StringField('Ваше имя', validators=[
        DataRequired(message="Пожалуйста, укажите ваше имя."),
        Length(min=2, max=100, message="Имя должно содержать от 2 до 100 символов.")
    ])

    email = StringField('Ваша почта', validators=[
        Email(message="Некорректный формат email."),
        Length(max=120),
    ])

    # Используем TelField для семантической корректности
    phone = TelField('Ваш телефон', validators=[
        DataRequired(message="Пожалуйста, укажите ваш телефон."),
        # Регулярное выражение для проверки международного формата, например +71234567890
        Regexp(r'^\+\d{11,15}$', message="Некорректный формат телефона. Ожидается формат +71234567890.")
    ])

    lesson_type = SelectField('Тип занятий', choices=[
        ('individual_online', 'Индивидуально'),
        ('group_online', 'Групповое занятие'),
        ('unsure', 'Еще не знаю / Нужна консультация')
    ], validators=[DataRequired(message="Пожалуйста, выберите тип занятий.")])

    consent = BooleanField('Даю согласие на обработку персональных данных', validators=[
        DataRequired(message="Необходимо дать согласие на обработку данных.")
    ])

    submit = SubmitField('Записаться')