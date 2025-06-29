from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,SubmitField,SelectField
from wtforms.validators import DataRequired, Length, EqualTo, length
from flask_wtf.csrf import CSRFProtect
class login(FlaskForm):
    username=StringField('username',validators=[DataRequired(),length(min=5,max=10)])
    password = PasswordField('password', validators=[DataRequired(), length(min=5, max=10)])
    submit=SubmitField('login')
class updatepassword(FlaskForm):
    user_name = StringField('user_name', validators=[DataRequired(), length(min=5, max=10)])
    pass_word = PasswordField('pass_word', validators=[DataRequired(), length(min=5, max=10)])
    confirm_pass_word = PasswordField('confirm_pass_word', validators=[DataRequired(), length(min=5, max=10)])
    submit_password = SubmitField('update password')
class addpapers(FlaskForm):
    choices=[(0,'Select Paper Type'),('International','International'),('National','National'),('Local','Local')]
    paper_name = StringField('paper_name', validators=[DataRequired(), length(min=2, max=40)])
    paper_type = SelectField('paper_type',choices=choices)
    submit_paper = SubmitField('Add Paper')


class addcategories(FlaskForm):
    category_name = StringField('category_name', validators=[DataRequired(), length(min=2, max=40)])
    category_link = StringField('category_link', validators=[DataRequired(), length(min=10, max=200)] )
    submit_category = SubmitField('Add category')

class choicesform(FlaskForm):
    zone = SelectField('zone', choices=[('0', 'Select zone'), ('Local', 'Local'), ('National', 'National'),
                                        ('International', 'International')])
    newspaper = SelectField('newspaper', choices=[])
    newscategory = SelectField('newscategory', choices=[])
    submit = SubmitField('Search News')

