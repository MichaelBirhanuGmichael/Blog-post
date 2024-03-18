from flask import Flask, abort, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm , RegisterForm , LoginForm ,CommentForm
from functools import wraps
# from flask_gravatar import Gravatar
from hashlib import md5

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)       

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

##CONFIGURE TABLES


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    # author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
        #Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    #Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="posts")
    comments  = relationship("Comment" , back_populates="parent_post")
    
class User(UserMixin,db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    #This will act like a List of BlogPost objects attached to each User. 
    #The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment" , back_populates="comment_author") 
    
    def avatar(self, size):
        # Generate MD5 hash of the user's email
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        # Default Gravatar URL with identicon (default) if image not found
        default_url = f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'
        # Personalized Gravatar URL without default identicon
        personalized_url = f'https://www.gravatar.com/avatar/{digest}?s={size}'
        
        # Check if the personalized Gravatar image exists
        # Sending a HEAD request to the personalized URL and checking the status code (200 means the image exists)
        exists = requests.head(personalized_url).status_code == 200
        if exists:
            # If personalized Gravatar image exists, return the personalized URL
            return personalized_url
        else:
            # If personalized Gravatar image doesn't exist, return the default URL with identicon
            return default_url

class Comment(db.Model):
    __tabelname__ = "comments"
    id  = db.Column(db.Integer,primary_key = True )
    author_id  = db.Column(db.Integer , db.ForeignKey("users.id"))
    comment_author = relationship("User" , back_populates="comments")
    text = db.Column(db.Text , nullable = False)
    post_id  = db.Column(db.Integer , db.ForeignKey("blog_posts.id"))
    parent_post=relationship("BlogPost" , back_populates="comments" )

login_manager = LoginManager()
login_manager.init_app(app)
@login_manager.user_loader
def load_user(user_id):
    # Assuming you have a User model with an 'id' attribute
    return db.session.get(User , user_id )

with app.app_context():   
 db.create_all()


def admin_only(function):
    @wraps(function)
    def decorated_function(*args ,**kwargs):
       if current_user.id != 1:
           return abort(403)
       return function(*args , **kwargs)
    return decorated_function

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register' , methods  = ["GET" , "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        password  = form.password.data
        hashed_password  = generate_password_hash(password=password ,method='pbkdf2:sha256' , salt_length=8)
        name = form.name.data
        user  = db.session.query(User).filter_by(email = email).first()
        
        if user :
            flash("You'have already signed up with that email , log in instead!")
            
        else: 
            new_user  = User(
                name= name ,
                password = hashed_password,
                email = email,
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('get_all_posts'))
    return render_template("register.html" , form = form )


@app.route('/login' , methods = ["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user  = db.session.query(User).filter_by(email = form.email.data).first()
        if user :
           if check_password_hash(user.password , password=form.password.data):
                  login_user(user)
                  return redirect(url_for('get_all_posts'))
           else :
                   flash('password incorrect , please try again')
                 
        else:
                 flash('That email doesnt exist please try again') 
                 return redirect(url_for('login'))     
    return render_template("login.html" , form = form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>" , methods = ["GET" , "POST"])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))
        new_comment = Comment(
            text = form.comment.data,
            parent_post  = requested_post,
            comment_author = current_user
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('get_all_posts'))
        

    return render_template("post.html", post=requested_post, current_user= current_user, form = form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post" , methods = ["GET" , "POST"])
@admin_only 
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form ,current_user= current_user)


@app.route("/edit-post/<int:post_id>")
@admin_only 
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form ,current_user= current_user)


@app.route("/delete/<int:post_id>")
@admin_only 
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
