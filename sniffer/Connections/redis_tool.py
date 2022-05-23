import redis

# r = redis.StrictRedis(host='localhost', port=6379, db=0)
r = redis.StrictRedis(host='sniffer0', port=6379, db=0)

d = {
      "16777215": "BROADCAST",
      "2325608": "CAM IgorG",
      "2146147": "CAM IgorG2",
      "1587497": "AIR IgorG",
      "2171688": "MAG IgorG",
      "2333670": "SMOKE IgorG",
      "1583195": "IgorG panel",
      "2326320": "Tanya panel",
}

# for key, val in d.iteritems():
#     r.delete(key)

d2 = {
        "16777215": {
            "alias": "BROADCAST"
        },
        "2325608": {
            "alias": "CAM IgorG",
            "dev_type_id": "37"
        },
        "2146147": {
            "alias": "CAM IgorG2"
        },
        "1587497": {
            "alias": "AIR IgorG"
        },
        "2171688": {
            "alias": "MAG IgorG"
        },
        "2333670": {
            "alias": "SMOKE IgorG"
        },
        "1583195": {
            "alias": "IgorG panel"
        },
        "2326320": {
            "alias": "Tanya panel"
        }
}

d3 = {
    "111": {
        "typ_id": "35",
        "nam": "MAG igor"
    }
}

# name = '111'
# for key, val in d3[name].iteritems():
#     r.hset(name, key, val)

print r.hget("1583195", "alias")
print 'Exists', r.hexists("1583195", "alias")

for sn, val_dict in d2.iteritems():
    for key, val in val_dict.iteritems():
        r.hset(sn, key, val)


# print 'type ID:', r.hget(name, 'type_id')
# print 'alias:', r.hget(name, 'name')
r.delete("2325609")
r.delete("111")
print 'ALL:', r.hgetall("2325609")
print 'ALL:', r.hgetall("111")
print r.hget("1583195", "alias")
print 'Exists', r.hexists("1583195", "alias")