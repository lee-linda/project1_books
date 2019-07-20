# Project 1

Web Programming with Python and JavaScript:
Build a book review website. Users will be able to register for the website and then log in using their username and password. Once they log in, they will be able to search for books, leave reviews for individual books, and see the reviews made by other people. Use a third-party API by Goodreads, to pull in ratings from a broader audience. Finally, users will be able to query for book details and book reviews programmatically via this website’s API.

https://courses.edx.org/courses/course-v1:HarvardX+CS50W+Web/course/

Heroku app:  
https://book-reader-cafe.herokuapp.com/  


Files:  
application.py: Flask application file.  
books.csv: Info of 5000 different books, each one has an ISBN number, a title, an author, and a publication year.  
requirements.txt: Python packages that need to be installed in order to run this web application.  
helpers.py: Python file with helper functions used in application.py.  
import.py: Python file to import books.csv info into Heroku database.  


Setup:
# Install packages
$ pip install -r requirements.txt

# ENV Variables
$ export FLASK_APP = application.py # flask run  
$ export DATABASE_URL = Heroku Postgres DB URI  
$ export KEY = Goodreads API Key. # More info: https://www.goodreads.com/api  

