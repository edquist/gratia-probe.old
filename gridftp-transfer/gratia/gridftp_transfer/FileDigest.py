
# attampts to guarantee some level of uniqness to the file content
def getFileDigest(fileName):

    f = file(fileName)
    r = f.read(80)
    f.close()

    import os
    return str(os.stat(fileName)[1])+str(hash(r))
      
