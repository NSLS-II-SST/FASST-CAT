def repeat(s, exclaim):
    result = s * 3 
    if exclaim:
        result = result + '!!!'
    return result    

def main():
    print(repeat('Yay', False))
    print(repeat('Woo Hoo', True))

main()