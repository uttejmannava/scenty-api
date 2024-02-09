# Scenty API

## What does it do

Scenty API is a RESTful API with full CRUD functionality built in to host and serve perfume data from the fragrantica.com database.
The API uses a custom webscraping script using BeautifulSoup, stores scraped data (perfume info + reviews) in a PostgreSQL database, and is built with Flask infrastructure.

## Tech
- Python
- Flask
- BeautifulSoup
- PostgreSQL
- Postman

## Data

Perfumes:
- Name, Brand, Gender, Accords (notes), Images (bottle, brand), Rating, Number of ratings, Description

Reviews:
- Corresponding Perfume ID, Review Author, Review Date, Review Text

## Features currently being implemented

User authentication and sentiment analysis (NLTK) to determine aggregate scores for perfume based on user review data.
