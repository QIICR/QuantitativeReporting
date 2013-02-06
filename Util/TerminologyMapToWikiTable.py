import string, sys

def DropSpaces(s):
  i = 0
  while i<len(s)-1:
    if s[i] != ' ':
      break
    i = i+1

  j = len(s)-1
  while j>1:
    if s[j] != ' ':
      break
    j = j-1

  return s[i:j+1]

if len(sys.argv)<2:
  print 'Mapping table expected on input!'
  exit()

fName = sys.argv[1]
fIn = open(fName,'r')
lineCnt = 0
for line in fIn:
  lineCnt=lineCnt+1
  if lineCnt<4:
    continue

  items = string.split(line,',')
  labelId = DropSpaces(items[0])
  labelName = DropSpaces(items[1])
  propCategory = DropSpaces(items[2])
  propType = DropSpaces(items[3])
  propTypeMod = DropSpaces(items[4])
  color = DropSpaces(items[5][:-1])

  color=string.replace(color,';',',')

  print '|-'
  print '| ',labelId
  print '| ',labelName
  print '| style=\"background:',color,'\"|',color
  print '| ',propCategory
  print '| ',propType
  print '| ',propTypeMod
