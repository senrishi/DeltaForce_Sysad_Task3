from flask import Flask, session, redirect, jsonify, url_for, request, jsonify, render_template
import jwt


app = Flask(__name__)
app.secret_key = "damn"

admin_cred = ["notAdmin", "notSysAd"]
flag = "flag{YOU_ARE_ADMIN_LETS_GOO}"

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST', 'GET'])
def login():

    if request.method == 'POST':
        user = request.form['nm']
        password = request.form['pw']
        session['username'] = user  #username and password stored in the session
        session['password'] = password
        if user == admin_cred[0] and password == admin_cred[1]:
            encoded = jwt.encode({"username": "notAdmin", "isAdmin": True},key="", algorithm="none")
            return jsonify({"message": "Admin!!!!!!!", "token": encoded})
        elif user == admin_cred[0] and password != admin_cred[1]: 
            # reprompts the user to enter the correct password
            return render_template('login.html', error="Incorrect password for admin user.")
        else:
            encoded = jwt.encode({"username": f"{user}", "isAdmin": False}, key="",algorithm="none")
            return jsonify({"message": "Not an Admin", "token": encoded})

    else:
       return render_template('login.html')


@app.route('/admin')
def admin():
    token = request.args.get('token')
    if token:
        try:
            decoded = jwt.decode(token, key="", algorithms=["none"], options={"verify_signature": False})
            if decoded['isAdmin']:
                return jsonify({"message": "Admin access granted", "flag": flag})
            else:
                return jsonify({"message": "Not an Admin"})
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token expired"})
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token"})
    else:
        return jsonify({"message": "No token provided"})
if __name__ == '__main__':
    app.run(debug=True)
