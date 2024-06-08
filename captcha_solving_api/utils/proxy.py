def proxy2dict(proxy: str) -> dict:
    p = proxy.split('@', 1)
    if len(p) == 1:
        return {'server': p[0]}
    else:
        return {
            'server': p[1],
            'username': p[0].split(':')[0],
            'password': p[0].split(':')[1]
        }