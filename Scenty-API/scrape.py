import requests, time
from bs4 import BeautifulSoup

headers = {"User-Agent": 
           "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"}

def get_html(url, max_retries=3):
    # for wait-and-retry logic to bypass rate-limiting
    retries = 0
    
    while retries < max_retries:
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            return soup
        
        except requests.exceptions.RequestException as exc:
            print(f"error: {exc}")
            print(f"retrying: ({retries + 1}/{max_retries})")
            
            retries += 1

            time.sleep(5) 

#extractor function, deal with attribute errors
def extract(html, css_sel):
    try:
        return html.select_one(css_sel)
    except AttributeError:
        return None

def parse_info(html):
    name = html.find('div', id='toptop').text
    title = ''
    gender = []
    i = name.find('for')
    if i == -1:
        #assume unisex if 'for ____ (and) ____' missing in perfume name
        gender = ['men', 'women']
        title = name
    else:
        s = name[i+3:].split()
        if s[-1] != s[0]:
            gender.extend([s[0], s[-1]])
        else:
            gender.append(s[0])
        title = name[:i-1]

    infoSection = html.find_all('div', class_='cell small-12')[1]
    if infoSection:
        brand = extract(infoSection, 'div.cell.small-6.text-center span[itemprop="name"]').get_text()
        brandImage = extract(infoSection, 'div.cell.small-6.text-center img[itemprop="logo"]').get('src')

        accordSection = infoSection.find_all('div', class_='accord-bar')
        accords = []
        for accord in accordSection:
            accords.append(accord.get_text())
        
        bottleImage = extract(infoSection, 'div.cell.small-6.text-center img[itemprop="image"]').get('src')

        rating = extract(infoSection, 'div.small-12.medium-6.text-center span[itemprop="ratingValue"]').get_text()
        ratingCount = extract(infoSection, 'div.small-12.medium-6.text-center span[itemprop="ratingCount"]').get_text()
        ratingCount = int(ratingCount.replace(",",""))

        desc = extract(infoSection, 'div.cell.small-12[itemprop="description"]').select_one('p').get_text().rstrip()

        return {
            "name": title,
            "gender": gender,
            "brand": brand,
            "brandImageURL": brandImage,
            "accords": accords,
            "bottleImageURL": bottleImage,
            "rating": rating,
            "ratingCount": ratingCount,
            "description": desc,
            "reviews": parse_reviews(html)
        }
    else:
        return('No information on this perfume')

def parse_reviews(html):
    reviewSection = html.find('div', class_='grid-x grid-padding-x grid-margin-y')

    if reviewSection:
        # find first 20 div elements with the class 'cell fragrance-review-box'
        review_boxes = reviewSection.select('div.cell.fragrance-review-box:nth-child(-n+21)')
        reviews = []
        for review_box in review_boxes:
            review_box = review_box.find('div', class_='grid-x')
            if review_box != None:

                review_body = extract(review_box, 'div.cell.small-10.flex-container.flex-dir-column div.flex-child-auto').text
                review_author = extract(review_box, 'div.cell.small-10.flex-container.flex-dir-column div.flex-child-shrink p b.idLinkify').text
                review_time = extract(review_box, 'div.cell.small-10.flex-container.flex-dir-column div.flex-child-shrink p span[itemprop="datePublished"]').get('content')
                
                item = {
                    "author": review_author,
                    "date": review_time,
                    "body": review_body
                }
            
            else: #None for all
                #don't add anything
                pass
            
            reviews.append(item)
        
        return reviews
    
    else:
        return('No reviews on this page.')
    
def scrape_all(url):
    html = get_html(url)
    if html:
        return parse_info(html)
    else:
        return None

# def scrape_reviews(url):
#     html = get_html(url)
#     if html:
#         return parse_reviews(html)
#     else:
#         return None