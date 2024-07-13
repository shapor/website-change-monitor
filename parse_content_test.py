import sys
from bs4 import BeautifulSoup, Comment
import re
from gcf.main import parse_content

def main(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    
    parsed_content = parse_content(html_content, strip=True)
    print(parsed_content)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python parse_content_test.py <path_to_html_file>")
        sys.exit(1)
    
    main(sys.argv[1])
