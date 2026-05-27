import urllib.request, json

BASE = "http://127.0.0.1:8000/api/v1"
HEADERS = {"Content-Type": "application/json"}

def post(path, body, token=None):
    h = {**HEADERS}
    if token:
        h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(), headers=h, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

# 1. Main admin login
s, d = post("/auth/login", {"username": "admin", "password": "admin"})
main_admin_token = d["access_token"]
print(f"[1] Main admin login: {s}")

# 2. Main admin creates sub-admin and sub-mod
s, d_sa = post("/admin/users", {"role": "admin"}, main_admin_token)
sub_admin_user, sub_admin_pw = d_sa["username"], d_sa["generated_password"]
print(f"[2a] Main admin creates sub-admin: {s} {sub_admin_user}")

s, d_sm = post("/admin/users", {"role": "moderator"}, main_admin_token)
sub_mod_user, sub_mod_pw = d_sm["username"], d_sm["generated_password"]
print(f"[2b] Main admin creates sub-mod: {s} {sub_mod_user}")

# 3. Sub-admin login
s, d = post("/auth/login", {"username": sub_admin_user, "password": sub_admin_pw})
sub_admin_token = d["access_token"]

# 4. Sub-admin tries to create sub-admin (expect 403)
s, d = post("/admin/users", {"role": "admin"}, sub_admin_token)
print(f"[4] Sub-admin creates admin (expect 403): {s}")

# 5. Sub-admin creates sub-mod2 (expect 201)
s, d_sm2 = post("/admin/users", {"role": "moderator"}, sub_admin_token)
print(f"[5] Sub-admin creates mod (expect 201): {s}")

# 6. Sub-mod login
s, d = post("/auth/login", {"username": sub_mod_user, "password": sub_mod_pw})
sub_mod_token = d["access_token"]

# 7. Sub-admin creates room (expect 201)
s, d = post("/rooms/", {"name": "admin-room", "description": "test"}, sub_admin_token)
print(f"[7] Sub-admin creates room (expect 201): {s}")

# 8. Sub-mod creates room (expect 201)
s, d = post("/rooms/", {"name": "mod-room", "description": "test"}, sub_mod_token)
print(f"[8] Sub-mod creates room (expect 201): {s}")

# 9. Anonymous join 1 and 2
s, d1 = post("/auth/join", {})
normal_token_1 = d1["access_token"]
normal_user_1 = d1["username"]

s, d2 = post("/auth/join", {})
normal_token_2 = d2["access_token"]
normal_user_2 = d2["username"]
print(f"[9] Created normal users: {normal_user_1}, {normal_user_2}")

# 10. Normal dm normal (expect 200)
s, d = post(f"/dm/{normal_user_2}", {"content": "hi"}, normal_token_1)
print(f"[10] Normal dm Normal (expect 200): {s}")

# 11. Normal dm mod (expect 200)
s, d = post(f"/dm/{sub_mod_user}", {"content": "hi"}, normal_token_1)
print(f"[11] Normal dm Mod (expect 200): {s}")

# 12. Normal dm admin (expect 403)
s, d = post(f"/dm/{sub_admin_user}", {"content": "hi"}, normal_token_1)
print(f"[12] Normal dm Admin (expect 403): {s}")

# 13. Admin dm normal (expect 200)
s, d = post(f"/dm/{normal_user_1}", {"content": "hello"}, sub_admin_token)
print(f"[13] Admin dm Normal (expect 200): {s}")

# 14. Mod dm Admin (expect 200)
s, d = post(f"/dm/{sub_admin_user}", {"content": "sup"}, sub_mod_token)
print(f"[14] Mod dm Admin (expect 200): {s}")
