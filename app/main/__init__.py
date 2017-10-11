from flask import Blueprint

main = Blueprint("main", __name__, static_url_path='/main/static', static_folder='./static',
                          template_folder='./templates')

from . import blog