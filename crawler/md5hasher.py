import hashlib

def hashing(url):
    __MD5 = hashlib.new('md5')
    __MD5.update(url.encode())
    URLHash = __MD5.hexdigest()
    return URLHash
