pin_groups = ((0, 2, 4, 6, 8, 10, 12), (1, 3, 5, 7, 9, 11, 13))

l = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]
print(pin_groups)

# the result shape will always produce from shortest row
lt = list(map(list, zip(*l)))
pg = list(map(list, zip(*pin_groups)))
# [
#     [1, 5, 9],
#     [2, 6, 10],
#     [3, 7, 11],
#     [4, 8, 12]
# ]
print(pg)
t = ((1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11, 12))

# the result shape will always produce from shortest row
tt = tuple(zip(*l))
pgtt = tuple(zip(*pin_groups))
# (
#     (1, 5, 9),
#     (2, 6, 10),
#     (3, 7, 11),
#     (4, 8, 12)
# )
print(tt)
print(pgtt)
