from flask import Flask,render_template,redirect,session,request,url_for,jsonify,json
from  flask_sqlalchemy import SQLAlchemy
from constant import price,adminname,adminpassword
from sqlalchemy import LargeBinary,BINARY
import psycopg2
import base64
from io import BytesIO
from PIL import Image
from img2txt import extract_data
from random import randrange

app = Flask(__name__)
app.secret_key = 'thwe'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:toor@localhost:5432/CycleTicket'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.app_context().push()

class Users(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable= False)
    password = db.Column(db.String(100), nullable= False)

class Orders(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, nullable= False)
    user_name = db.Column(db.String(100), nullable = False)
    tickets = db.Column(db.String(1000), nullable = False)
    image = db.Column(LargeBinary)
    verify = db.Column(db.String(50),nullable= False)


class TicketWinner(db.Model):
    id = db.Column(db.Integer,primary_key = True)
    winner_ticket = db.Column(db.String(100), nullable = False)
    winner_verify = db.Column(db.String(100), nullable = False)
    expired = db.Column(db.Integer)


db.create_all()


@app.route('/')
def home():

    validate_user = None
    tickets = []
    selected_ticket = []
    orders= Orders.query.all()
    winners = TicketWinner.query.order_by(TicketWinner.id.desc()).first()
    if winners:
        if winners.expired == 1:
            return render_template('home.html',winners= winners)
    if orders:
        for order in orders:
            if order.verify == "Accepted" or order.verify == 'Pending':
                pending_ticket = order.tickets.split(',')
            for i in pending_ticket:
                selected_ticket.append(i)
    for i in range(1,101):
        tickets.append(f"{i:03}")
    if session and session['username']:
        validate_user = session['username']
        return render_template('home.html',username = validate_user, tickets = tickets, selected_ticket = selected_ticket)
    # if  not session:
    #     session['admin_username'] = adminname
    #     winners = TicketWinner.query.order_by(TicketWinner.id.desc()).first()
    #     if winners:
    #         if winners.expired == 1:
    #             return render_template('home.html',winners= winners)
    #         if winners.expired == 0:
    #             block_all_ticket = 'blockall'
    #             validate_user = session['admin_username']
    #             return render_template('home.html',admin_username = validate_user, tickets = tickets, block_all_ticket = block_all_ticket)
    #     validate_user = session['admin_username']
    #     return render_template('home.html',admin_username = validate_user, tickets = tickets, selected_ticket = selected_ticket)
    return render_template('home.html')
    
        
@app.route("/login", methods = ['POST', 'GET'])
def login():
    win = ''
    loose = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = Users.query.filter_by(username = username,password = password).first()
        if username == adminname and password == adminpassword:
            session['admin_username']= adminname
            return redirect('/admin')
        if user:
            winners= TicketWinner.query.order_by(TicketWinner.id.desc()).first() 
            if winners:
                if winners.expired == 1:
                    if user.username == username and user.password == password:
                        session['username'] = username
                        valid_user = session['username']
                        orders = Orders.query.all()
                        for order in orders:
                            if order.verify == "Accepted":
                                pending_ticket = order.tickets.split(',')
                                if winners.winner_ticket in pending_ticket:
                                    winner_info = Orders.query.get(order.id)
                                    if winner_info.user_name == valid_user:
                                        winnerticket = winners.winner_ticket
                                        winnername = valid_user
                                        win = 'win'
                                        return render_template('congrat.html',win = win, winnername = winnername, winnerticket = winnerticket,username = valid_user)
                                    else:
                                        session['username'] = username
                                        valid_user = session['username']
                                        loose = 'loose'
                                        return render_template('congrat.html',loose = loose,username = valid_user)
            if user.username == username and user.password == password:
                session['username'] =  user.username
                return redirect('/') 
    return render_template('login.html',)
        
            
            
    

@app.route("/register", methods = ['POST', 'GET'])
def register():
    if request.method == 'POST':
        name = request.form['username']
        pwd = request.form['password']
        user = Users(username = name, password = pwd)
        db.session.add(user)
        db.session.commit()
        return redirect('/')
    return render_template('register.html')

@app.route('/ticket_order', methods = ['POST','GET'])
def ticket_order():
    form_selected_tickets = request.form.getlist("ticket[]")
    
    if len(form_selected_tickets):
        totalprice = len(form_selected_tickets) * price
        selected_ticket = ""
        for ticket in form_selected_tickets:
            if selected_ticket:
                selected_ticket += ','
            selected_ticket += ticket
        if session and session['username']:
            validUser = session['username']
            user = Users.query.filter_by(username = validUser).first()
            validUserId = user.id
            if validUser:
                orders ={}
                orders = {'user_id':validUserId, 'user_name':validUser, 'tickets':selected_ticket}
                json_orders = json.dumps(orders)
                session['orders'] = json_orders
                return render_template('order.html',username = validUser,tickets = form_selected_tickets,totalprice=totalprice,price=price)
            else:
                return redirect('/login')
        else:
            return redirect('/login')
    else:
        return redirect('/')
    

@app.route('/update' , methods=['POST'])
def update():
    if request.method == 'POST':
        image = request.files['img']
        upload_image = image.read()
        get_session_data= session['orders']
        get_session_data = json.loads(get_session_data)
        order_data = Orders(user_id=get_session_data['user_id'],user_name=get_session_data['user_name'],tickets=get_session_data['tickets'],image=upload_image,verify='Pending')
        db.session.add(order_data)
        db.session.commit()
        session.pop('orders',False)
        if session and session['username']:
            validuser = session['username']
            username_order= Orders.query.order_by(Orders.id.desc()).first()
            user_order_id = username_order.id
            return redirect(url_for('check', checkid = user_order_id))
    return render_template('order.html')  
 

            
@app.route('/check/<int:checkid>',methods=['GET','POST'])
def check(checkid):
    if session and session['username']:
        validate_user = session['username']
        data = Orders.query.get(checkid)
        if data:
            pending_tickets = data.tickets.split(',')
            total_price = len(pending_tickets) * price
            return render_template('check.html',checking = data.verify,username=validate_user,data = data, total_price = total_price)
    return render_template('/')

@app.route('/admin')
def admin():
    orders = Orders.query.all()
    if session and session['admin_username']:
        valid_user = session['admin_username']
        order_tickets = []
        order_pending = []
        winner_info = []
        winners= TicketWinner.query.order_by(TicketWinner.id.desc()).first()
        if winners:
            for order in orders:
                if order.verify == "Accepted":
                    pending_ticket = order.tickets.split(',')
                    if winners.expired == 0:
                        if winners.winner_ticket in pending_ticket:
                            winnerticket = winners.winner_ticket
                            confirm_winner = Orders.query.get(order.id)
                            file = BytesIO(confirm_winner.image)
                            image = Image.open(file)
                            image_string_read = extract_data(image)
                            order.image = base64.b64encode(order.image).decode('utf-8')
                            temp_dict = order.__dict__
                            temp_dict.update({"payment_info": image_string_read})
                            winner_info.append(temp_dict)
                            return render_template('admin_dashboard.html', confirm_winner = confirm_winner,winner_info= winner_info, admin_username = valid_user,winnerticket = winnerticket)
        if orders:
            for order in orders:
                if order.image :
                    file = BytesIO(order.image)
                    image = Image.open(file)
                    image_string_read = extract_data(image)
                    order.image = base64.b64encode(order.image).decode('utf-8')
                    if order.verify == 'Pending':
                        temp_dict = order.__dict__
                        temp_dict.update({"payment_info": image_string_read})
                        order_pending.append(temp_dict)
                    if not order.verify == 'Pending':
                        temp_dict = order.__dict__
                        temp_dict.update({"payment_info": image_string_read})
                        order_tickets.append(temp_dict)
            return render_template('admin_dashboard.html', order_tickets = order_tickets,admin_username = valid_user, order_pending = order_pending)
    return render_template('admin_dashboard.html', order_tickets = order_tickets,admin_username = valid_user, order_pending = order_pending)
    
@app.route('/admin_accept/<int:orderid>')
def admin_accept(orderid):
    if orderid:
        data = Orders.query.get(orderid)
        data.verify = 'Accepted'
        db.session.commit()
        return redirect('/admin')
    return redirect('/')

@app.route('/admin_reject/<int:orderid>')
def admin_reject(orderid):
    if orderid:
        data = Orders.query.get(orderid)
        data.verify = "Rejected"
        db.session.commit()
        return redirect('/admin')
    return redirect('/')

@app.route('/userprofile')
def userprofile():
    if session and session['username']:
        valid_user = session['username']
        user=Users.query.filter_by(username=valid_user).first()
        my_order=Orders.query.filter_by(user_id=user.id).order_by(Orders.id.desc())
        orders=[]
        for o in my_order:
            tem=o.__dict__
            tem['price']=len(tem['tickets'].split(','))*price
            orders.append(tem)
        return render_template('userprofile.html',orders = orders,username= valid_user)
    return redirect('/')

@app.route('/choose_winner')
def choose_winner():
    selected_ticket = []
    ticket_no=f"{randrange(0,101):03}"
    # ticket_no = '004'
    check_order = Orders.query.all()
    if ticket_no:
        for order in check_order:
            if order.verify == "Accepted":
                pending_ticket = order.tickets.split(',')
                for i in pending_ticket:
                    selected_ticket.append(i)
        if ticket_no in selected_ticket:
            winner = TicketWinner(winner_ticket=ticket_no,winner_verify = 'OK',expired = 0)
            db.session.add(winner)
            db.session.commit()
            return redirect('/admin')
    return render_template('admin.html')


@app.route('/logout')
def logout():
    session.pop('username',False)
    return redirect('/')

@app.route('/adminlogout')
def adminlogout():
    session.pop('admin_username',False)
    return redirect('/')

@app.route('/releaseticket')
def releaseticket():
    winners= TicketWinner.query.order_by(TicketWinner.id.desc()).first()
    if winners:
        winners.expired = 1
        db.session.commit()
        session.pop('admin_username',False)
        return redirect('/')
    session.pop('admin_username',False)
    return redirect('/')




if __name__ == '__main__':
    app.run(debug=True)