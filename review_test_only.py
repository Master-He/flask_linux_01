"""
test 1
"""
# a = 1
# b = 2
# c = None
# if not all([a,b,c]):
#     print("参数不全")
# else:
#     print("OK")


"""
test 2
"""
# data1 = {
#     "user":"name",
#     "age":"18"
# }
#
# data1.to_dict()


"""
test 3
enumerate() 函数用于将一个可遍历的数据对象(如列表、元组或字符串)
组合为一个索引序列，同时列出数据和数据下标，
一般用在 for 循环当中。
"""
# seq = ["one", "two", "three"]
# for element in enumerate(seq):
#     print(element)
#
# for i,element in enumerate(seq):
#     print(i,element)
#
# print(enumerate(seq))


"""
test 4
复习装饰期
"""
# import functools
#
# def decorator(func):
#     def wrapper(*args, **kwargs):
#         print("装饰...")
#         return func(*args, **kwargs)
#
#     return wrapper
#
#
# def decorator2(func):
#     @functools.wraps(func)
#     def wrapper(*args, **kwargs):
#         print("装饰...")
#         return func(*args, **kwargs)
#
#     return wrapper
#
#
# @decorator
# def foo():
#     print("foo")
#
#
# @decorator2
# def haa():
#     print("haa")
#
#
# foo()
# print(foo.__name__)
#
#
# haa()
# print(haa.__name__)