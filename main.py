from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session as flask_session

app = Flask(__name__)
app.config['SECRET_KEY'] = 'silygyrflsefmenu lhkqanemcn520'
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///Assignment-cafes.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
db.init_app(app)



class User(db.Model):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    password: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    todos = relationship("TodoList", back_populates="user", cascade="all, delete-orphan")


class TodoList(db.Model):
    __tablename__ = "todo_list"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    user = relationship("User", back_populates="todos")
    cards = relationship("Card", back_populates="todo", cascade="all, delete-orphan")

class Card(db.Model):
    __tablename__ = "card"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    due_date: Mapped[str] = mapped_column(String(50), nullable=True)
    label: Mapped[str] = mapped_column(String(50), nullable=True)
    is_daily: Mapped[bool] = mapped_column(Boolean, default=False)
    is_weekly: Mapped[bool] = mapped_column(Boolean, default=False)
    is_yearly: Mapped[bool] = mapped_column(Boolean, default=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)

    todo_id: Mapped[int] = mapped_column(ForeignKey("todo_list.id"), nullable=False)
    todo = relationship("TodoList", back_populates="cards")


with app.app_context():
    db.create_all()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=['GET', 'POST'])
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        if not name or not email or not password:
            flash('All fields are required!', 'danger')
            return render_template("register.html")
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template("register.html")

        if len(password) < 6:
            flash('Password must be at least 6 characters!', 'danger')
            return render_template("register.html")
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered!', 'danger')
            return render_template("register.html")
        hashed_password = generate_password_hash(password)
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template("register.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", '').strip()

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["user_name"] = user.name
            flash(f'welcome back,{user.name}!', 'success')
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password", 'danger')
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if 'user_id' not in flask_session:
        flash("Please login first!", "warning")
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    todos = TodoList.query.filter_by(user_id=user.id).all()

    total_tasks = sum(len(todo.cards) for todo in todos)
    completed_tasks = sum(1 for todo in todos for card in todo.cards if card.completed)

    stats = {
        "total_lists": len(todos),
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        "pending_tasks": total_tasks - completed_tasks
    }
    return render_template("dashboard.html", user=user, todos=todos, stats=stats)


@app.route('/add_todo', methods=['GET', 'POST'])
def add_todo():
    if 'user_id' not in flask_session:
        flash("Please login first", 'warning')
        return redirect(url_for("login"))
    if request.method == 'POST':
        title = request.form.get("title", "").strip()
        description = request.form.get("description", '').strip()

        if not title:
            flash('Title is required!', 'danger')
            return render_template("add_todo.html")
        user_id = flask_session.get('user_id')
        if not user_id or not isinstance(user_id, int):
            flash('Invalid user session!', 'danger')
            return redirect(url_for('logout'))

        new_todo = TodoList(title=title, description=description, user_id=user_id)
        db.session.add(new_todo)
        db.session.commit()

        flash("Todo list created successfully!", "success")
        return redirect(url_for("dashboard"))
    return render_template("add_todo.html")


@app.route("/todo/<int:todo_id>")
def view_todo(todo_id):
    if "user_id" not in flask_session:
        flash("Please login first!", 'warning')
        return redirect(url_for('login'))
    todo = TodoList.query.get_or_404(todo_id)
    if todo.user_id != session['user_id']:
        flash('You do not have permission to view this list!', 'danger')
        return redirect(url_for('dashboard'))

    return render_template("view_todo.html", todo=todo)


@app.route('/add_card/<int:todo_id>', methods=['GET', 'POST'])
def add_card(todo_id):
    if "user_id" not in flask_session:
        flash('please login first', 'warning')
        return redirect(url_for('login'))
    todo = TodoList.query.get_or_404(todo_id)
    if todo.user_id != flask_session['user_id']:
        flash('you do not have permission', "danger")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date = request.form.get('due_date', '').strip()
        label = request.form.get('label', '').strip()
        is_daily = bool(request.form.get('id_daily'))
        is_weekly = bool(request.form.get('is_weekly'))
        is_yearly = bool(request.form.get('is_yearly'))
        if not title:
            flash('Card title is required!', 'danger')
            return render_template("add_card.html", todo=todo)
        new_card = Card(title=title, description=description, due_date=due_date, label=label, is_daily=is_daily,
                        is_weekly=is_weekly, is_yearly=is_yearly, todo_id=todo_id)
        db.session.add(new_card)
        db.session.commit()
        flash('Task added successfully!', 'success')
        return redirect(url_for("view_todo", todo_id=todo_id))
    return render_template('add_card.html', todo=todo)


@app.route('/complete_card/<int:card_id>')
def complete_card(card_id):
    if "user_id" not in flask_session:
        flash('please login first', 'warning')
        return redirect(url_for('login'))

    card = Card.query.get_or_404(card_id)
    todo = TodoList.query.get(card.todo_id)
    if todo.user_id != session['user_id']:
        flash('you do not have permission', "danger")
        return redirect(url_for('dashboard'))

    card.completed = not card.completed
    db.session.commit()

    status = "completed" if card.completed else "uncompleted"
    flash(f'Task {status}!', 'success')
    return redirect(url_for('view_todo', todo_id=todo.id))


@app.route('/delete_card/<int:todo_id>')
def delete_todo(todo_id):
    if 'user_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))

    todo = TodoList.query.get_or_404(todo_id)
    if todo.user_id != session['user_id']:
        flash('You do not have permission!', 'danger')
        return redirect(url_for('dashboard'))

    db.session.delete(todo)
    db.session.commit()

    flash('Todo list deleted successfully!', 'success')
    return redirect(url_for('dashboard'))



@app.route("/delete_card/<int:card_id>")
def delete_card(card_id):
    if 'user_id' not in flask_session:
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))

    card = Card.query.get_or_404(card_id)
    todo = TodoList.query.get(card.todo_id)

    if todo.user_id != flask_session['user_id']:
        flash('You do not have permission!', 'danger')
        return redirect(url_for('dashboard'))

    db.session.delete(card)
    db.session.commit()

    flash('Task deleted successfully!', 'success')
    return redirect(url_for('view_todo', todo_id=todo.id))

@app.route("/logout")
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=True)
