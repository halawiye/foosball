from flask import Flask, redirect, render_template, request, url_for, flash
from flask.ext.sqlalchemy import SQLAlchemy
from datetime import datetime
import config as cfg

app = Flask(__name__)

app.secret_key = cfg.KEY
app.config["DEBUG"] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
    username=cfg.USER,
    password=cfg.PASSWORD,
    hostname=cfg.HOST,
    databasename=cfg.DB,
)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299

db = SQLAlchemy(app)

class Game(db.Model):

    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime)
    player1a = db.Column(db.Integer)
    player1b = db.Column(db.Integer)
    player2a = db.Column(db.Integer)
    player2b = db.Column(db.Integer)
    oneWin = db.Column(db.Boolean)
    diff1a = db.Column(db.Float)
    diff1b = db.Column(db.Float)
    diff2a = db.Column(db.Float)
    diff2b = db.Column(db.Float)

class Player(db.Model):

    __tablename__ = "players"

    pid = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    played = db.Column(db.Integer)
    wins = db.Column(db.Integer)
    losses = db.Column(db.Integer)
    differential = db.Column(db.Integer)
    win_pct = db.Column(db.Float)
    streak = db.Column(db.Integer)
    rating = db.Column(db.Float)
    streak_peak = db.Column(db.Integer)
    streak_trough = db.Column(db.Integer)
    rating_peak= db.Column(db.Float)
    rating_trough = db.Column(db.Float)
    differential_peak = db.Column(db.Integer)
    differential_trough = db.Column(db.Integer)
    last_played = db.Column(db.DateTime)
    sp_obtained = db.Column(db.DateTime)
    st_obtained = db.Column(db.DateTime)
    rp_obtained = db.Column(db.DateTime)
    rt_obtained = db.Column(db.DateTime)
    dp_obtained = db.Column(db.DateTime)
    dt_obtained = db.Column(db.DateTime)

def updateIndividual(p,win, game_time):
    p.played += 1
    p.last_played = game_time
    if(win):
        p.wins += 1
        p.differential += 1
        p.streak = p.streak + 1 if p.streak >= 0 else 1
        if p.differential > p.differential_peak:
            p.differential_peak = p.differential
            p.dp_obtained = game_time
        if p.streak > p.streak_peak:
            p.streak_peak = p.streak
            p.sp_obtained = game_time
    else:
        p.losses += 1
        p.differential -= 1
        p.streak = p.streak -1 if p.streak <= 0 else -1
        if p.differential < p.differential_trough:
            p.differential_trough = p.differential
            p.dt_obtained = game_time
        if p.streak < p.streak_trough:
            p.streak_trough = p.streak
            p.st_obtained = game_time
    p.win_pct = 100*p.wins/p.played


def updateElo(ps, wins, game_time = datetime.utcnow()):
    #validate lists
    winners = [(ps[i],ps[i].rating) for i in range(len(ps)) if wins[i] == 1]
    losers = [(ps[i],ps[i].rating) for i in range(len(ps)) if wins[i] == 0]

    w_ensemble = 0;
    l_ensemble = 0;
    for p,r in winners:
        w_ensemble += r
    w_ensemble /= len(winners)
    for p,r in losers:
        l_ensemble += r
    l_ensemble /= len(losers)
    changes = []

    for p,r in winners:
        e_a = 1.0/(1 + pow(10,(l_ensemble - w_ensemble)/400))
        if (p.rating_peak < 2300 and p.played < 30):
            k = 40
        elif p.rating_peak < 2400:
            k = 20
        else:
            k = 10

        diff = k*(1 - e_a)
        p.rating = r + diff
        changes.append((p,diff))
        if(p.rating > p.rating_peak):
            p.rating_peak = p.rating
            p.rp_obtained = game_time

    for p,r in losers:
        e_a = 1.0/(1 + pow(10,(w_ensemble - l_ensemble)/400))
        if p.rating_peak < 2300 and p.played < 30:
            k = 40
        elif p.rating_peak < 2400:
            k = 20
        else:
            k = 10

        diff = -1*k*e_a
        p.rating = r + diff
        changes.append((p,diff))
        if (p.rating < p.rating_trough):
            p.rating_trough = p.rating
            p.rt_obtained = game_time

    return changes

@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    players=Player.query.all()
    if request.method == "GET":
        return render_template("main_page.html", players=players)

    game = Game(
        player1a = int(request.form["player1a"]),
        player2a = int(request.form["player2a"]),
        player1b = int(request.form["player1b"]),
        player2b = int(request.form["player2b"]),
        oneWin = int(request.form["oneWin"]),
        date = datetime.utcnow(),
        diff1a = 0,
        diff1b = 0,
        diff2a = 0,
        diff2b = 0)

    #validation goes here
    ids = [game.player1a, game.player1b, game.player2a, game.player2b]
    teams = [[game.player1a,game.player1b],[game.player2a,game.player2b]]


    for i in range(len(ids)):
        for j in range(i):
            if ids[i] == ids[j] and ids[i] != 0:
                error = "Duplicate player"+str(ids)
                return render_template("main_page.html", players=players, error=error)

    for i in range(2):
        teamZero = True
        for pid in teams[i]:
            teamZero = teamZero and pid == 0
        if teamZero:
            error = "Must have at least one player on each team"
            return render_template("main_page.html", players=players, error=error)


    ps = []
    wins = []

    for i in range(2):
        for pid in teams[i]:
            if pid == 0:
                continue
            p = Player.query.get(pid)
            if p is None:
                error = "Invalid player"
                return render_template("main_page.html", players=players, error=error)

            ps.append(p)
            if ((i == 0 and game.oneWin) or (i == 1 and not game.oneWin)):
                wins.append(1)
            else:
                wins.append(0)

    now = datetime.utcnow()
    changes = updateElo(ps, wins, now)
    for i in range(len(ps)):
        updateIndividual(ps[i],wins[i], now)

    for tup in changes:
        idx = ids.index(tup[0].pid)
        if idx == 0:
            game.diff1a = tup[1]
        elif idx == 1:
            game.diff1b = tup[1]
        elif idx == 2:
            game.diff2a = tup[1]
        elif idx == 3:
            game.diff2b = tup[1]

    db.session.add(game)
    db.session.commit()

    flash("Game recorded!")
    return redirect(url_for('index'))

@app.route('/stats', methods=['GET', 'POST'])
def stats():
    error = None
    players=Player.query.all()
    if request.method == "GET":
        return render_template("stats.html", players=players)
    else:
        p = Player.query.get(int(request.form["pid"]))
        if p is None:
            error = "Invalid player"
            return render_template("stats.html", players=players, error=error)
        else:
            return render_template("stats.html", players=players, p=p)

@app.route('/leaderboard', methods=['GET'])
def leaderboard():
    leader_stats = [("rating","Rating",True), ("win_pct","Win Percentage",True), ("streak","Streak",True)]
    if request.method == "GET":
        players=Player.query.all()
        leaders = {k : (n,sorted([(p.pid, p.name, vars(p)[k]) for p in players],key = lambda tup: -1 if tup[2] is None else tup[2], reverse = b)) for k,n,b in leader_stats}
        return render_template("leaderboard.html", leaders=leaders.items())

@app.route('/hof', methods=['GET'])
def hof():
    record_stats = [("played","Most Games Played",max), ("rating_peak","Highest Rating Achieved",max), ("rating_trough","Lowest Rating Achieved",min), ("streak_peak","Longest Win Streak",max), ("streak_trough","Longest Loss Streak",min)]
    if request.method == "GET":
        players=Player.query.all()
        vs = {n: f([(vars(p)[k],p.name) for p in players],key = lambda tup : tup[0]) for k,n,f in record_stats}

        return render_template("hof.html", vs=vs.items())

@app.route('/games', methods=['GET'])
def games():
    gs = Game.query.order_by(Game.date.desc()).all()
    players = Player.query.all()
    name_dict = {p.pid : p.name for p in players}
    name_dict[0] = ""
    game_list = [(name_dict[g.player1a], g.diff1a, name_dict[g.player1b], g.diff1b, name_dict[g.player2a], g.diff2a, name_dict[g.player2b], g.diff2b, g.date, 2 - g.oneWin, g.id) for g in gs]
    #should probably validate the above
    return render_template("games.html",game_list=game_list)
