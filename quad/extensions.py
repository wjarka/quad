from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)

import os
directory = os.path.join(os.getenv('VIRTUAL_ENV', '.'), 'migrations')
if (not os.path.isdir(directory)):
  raise Exception(f"No migrations directory at {directory}")

migrate = Migrate(directory=directory)