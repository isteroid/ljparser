import time

lst = [1,2,3,4,5,6,7,8,9,0]
dct = {1:2,3:4,5:6,7:8,9:10}
print('hello, bro!')
print(lst[None:None])
print(lst[2:None])
print(lst[None:7])
print(lst[2:7])
print(dct)
print(dct[1])
max_n = 200
for a in range(max_n):
	time.sleep(0.01)
	print('{}'.format(a), end='\r' if a<(max_n-1) else '\n')
