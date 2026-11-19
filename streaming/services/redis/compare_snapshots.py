import redis
r = redis.Redis(host='localhost', port=6379, db=0,decode_responses=True)


def compare_snapshots(old,new):
    # print(old,'from compare SNAPSHOTS')
    # print(new,'from compare SNAPSHOTS')
    oldSet = set()
    newSet = set()
    # print(old,'DIMA OLD')
    # print(new,'DIMA NEW')
    for item in old:
        oldSet.add(item.get('id'))

    for item in new:
        newSet.add(item.get('id'))
    # print(newSet,'NEW SET ')
    difference = newSet.difference(oldSet) # type of data set
    list_difference=list(difference) # type of data list
    return list_difference


# if __name__ == '__main__':
    # get_snapshots()
    # compare_snapshots(old,new)
