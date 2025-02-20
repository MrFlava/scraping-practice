import  requests

a = requests.get('https://webscraper.io/test-sites/e-commerce/allinone')

print(a.content)