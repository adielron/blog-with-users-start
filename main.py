from flask import Flask, render_template,abort, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
import os
from dotenv import load_dotenv
from sqlalchemy import ForeignKey, Integer, Column
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, Register_user, Login,CommentForm
from flask_gravatar import Gravatar
from functools import wraps


# load_dotenv('.env')
# SECRET_KEY = os.getenv("NAME")
# print(SECRET_KEY)

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)



gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


@login_manager.user_loader
def load_user(user_id):
    print(user_id)
    return User.query.get(user_id)

def admin(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        try:
            user_id = current_user.id
        except:
            print('no user')
            user_id=0
        if user_id != 1 or not current_user.is_authenticated:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function




##CONFIGURE TABLES
class User(db.Model,UserMixin):
    # Parent
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250),nullable=False,unique=True)
    password = db.Column(db.String(250),nullable=False)
    name = db.Column(db.String(250),nullable=False)

    posts = relationship('BlogPost', back_populates='author')
    comments = relationship('Comments', back_populates='comment_author')
# when typing .author you get in the User class
db.create_all()

class BlogPost(db.Model,UserMixin):
    # Child
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author = relationship('User', back_populates='posts')

    comments = relationship('Comments', back_populates='parent_post')



db.create_all()

class Comments(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(1000), nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comment_author = relationship('User', back_populates='comments')

    parent_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))
    parent_post = relationship('BlogPost', back_populates='comments')
db.create_all()



@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register',methods=["POST","GET"])
def register():
    form=Register_user()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('email alredy exists')
            return redirect(url_for('login'))
        else:
            password_hash = generate_password_hash(
                form.password.data,
                method='pbkdf2:sha256',
                salt_length=8)

            user=User(
                email=form.email.data,
                password=password_hash,
                name=form.name.data,
            )

            db.session.add(user)
            db.session.commit()
            login_user(user)
        return redirect(url_for('get_all_posts'))



    return render_template("register.html",form=form)


@app.route('/login',methods=["POST","GET"])
def login():
    form=Login()
    if form.validate_on_submit():
        email=form.email.data
        user=User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user=user)
                return redirect(url_for('get_all_posts',loged_in=True))
            else:
                flash('passwords dont match.', 'error')
                redirect('login')
        else:
            flash('email does not exist.','error')
            redirect('login')


    return render_template("login.html",form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form = CommentForm()
    if form.validate_on_submit():
        print('hello')
        if current_user.is_authenticated:
            comment = Comments(
            text=form.body.data,
            comment_author=current_user,
            parent_post=requested_post


            )
            print("sdasd")
            db.session.add(comment)
            db.session.commit()
        else:
            flash('you are not logged in')
            return redirect(url_for('login'))

    return render_template("post.html", user=current_user, post=requested_post, form=form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post",methods=["GET","POST"])
@admin
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
    return render_template("make-post.html", form=form, current_user=current_user)


@app.route("/edit-post/<int:post_id>")
@admin
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

    return render_template("make-post.html", form=edit_form,is_edit=True,current_user=current_user)


@app.route("/delete/<int:post_id>")
@admin
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
