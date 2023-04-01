#! /usr/local/bin/python3
from D2S import D2S

def main():
    d2s = D2S("/Users/admin/Downloads/test.d2s").parse()
    d2s.print()

if __name__=="__main__":
    main()
