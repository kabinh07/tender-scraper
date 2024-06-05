# keyword_list = []
with open("search_keywords.txt", "r") as f:
    keyword_list = list(f.read().split("\n"))

print(keyword_list)