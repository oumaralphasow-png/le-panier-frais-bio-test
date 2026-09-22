#!/usr/bin/env python3
import json, sys, urllib.request, urllib.error

BASE=(sys.argv[1] if len(sys.argv)>1 else "https://lepanierfraisbio.fr").rstrip("/")
checks=[]

def get(path):
    url=BASE+path
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            body=r.read().decode("utf-8","replace")
            return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8","replace")
    except Exception as e:
        return 0, repr(e)

def add(name,path,expect=200,contains=None):
    status,body=get(path)
    ok=(status==expect and (contains is None or contains in body))
    checks.append({"name":name,"path":path,"status":status,"ok":ok})
    return ok

add("Homepage","/",200,"Le Panier Frais Bio")
add("Health","/health",200)
add("Readiness","/health/ready",200,'"status":"ready"')
add("App config","/app-config",200,"lepanierfraisbio.fr")
add("PWA manifest","/manifest.webmanifest",200,"Le Panier Frais Bio")
add("Service worker","/service-worker.js",200,"lpfb-1-0-0-shell")

failed=[x for x in checks if not x["ok"]]
print(json.dumps({"base":BASE,"status":"PASS" if not failed else "FAIL","checks":checks},ensure_ascii=False,indent=2))
sys.exit(1 if failed else 0)
