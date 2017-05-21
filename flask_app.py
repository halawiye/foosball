from flask import Flask, redirect, render_template, request, url_for, flash
from flask.ext.sqlalchemy import SQLAlchemy
from datetime import datetime
import config as cfg
import math

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
    n_players = db.Column(db.Integer)

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
    team_rating = db.Column(db.Float)
    rd = db.Column(db.Float)
    team_rd = db.Column(db.Float)
    tau = db.Column(db.Float)
    team_tau = db.Column(db.Float)
    streak_peak = db.Column(db.Integer)
    streak_trough = db.Column(db.Integer)
    rating_peak= db.Column(db.Float)
    team_rating_peak = db.Column(db.Float)
    rating_trough = db.Column(db.Float)
    team_rating_trough = db.Column(db.Float)
    differential_peak = db.Column(db.Integer)
    differential_trough = db.Column(db.Integer)
    last_played = db.Column(db.DateTime)
    sp_obtained = db.Column(db.DateTime)
    st_obtained = db.Column(db.DateTime)
    rp_obtained = db.Column(db.DateTime)
    trp_obtained = db.Column(db.DateTime)
    rt_obtained = db.Column(db.DateTime)
    trt_obtained = db.Column(db.DateTime)
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

def newRatingPeriod(players, n_players):
    n_inactive = 2000
    csq = (350**2 - 50**2)/n_inactive
    if n_players < 4:
        for p in players:
            p.rd = min(math.sqrt((p.rd)**2 + csq),350)
    if n_players > 2:
        for p in players:
            p.team_rd = min(math.sqrt((p.team_rd)**2 + csq),350)

def updateGlicko(ps, wins, game_time):
    #validate lists
    ws = [ps[i] for i in range(len(ps)) if wins[i] == 1]
    ls = [ps[i] for i in range(len(ps)) if wins[i] == 0]

    w_solo = (len(ws) == 1)
    l_solo = (len(ls) == 1)
    winners = []
    losers = []


    if w_solo:
        winners = [(w, w.rating, w.rd) for w in ws]
    else:
        winners = [(w, w.team_rating, w.team_rd) for w in ws]
    if l_solo:
        losers = [(l, l.rating, l.rd) for l in ls]
    else:
        losers = [(l, l.team_rating, l.team_rd) for l in ls]

    w_ensemble = 0;
    w_rd = 0;
    l_ensemble = 0;
    l_rd = 0;
    for p,r,rd in winners:
        w_ensemble += r
        w_rd += rd*rd
    w_ensemble /= len(winners)
    w_rd = math.sqrt(w_rd)/len(winners)
    for p,r,rd in losers:
        l_ensemble += r
        l_rd += rd*rd
    l_ensemble /= len(losers)
    l_rd = math.sqrt(l_rd)/len(losers)
    changes = []

    q = math.log(10)/400
    def g(rd):
        return 1.0/(math.sqrt(1 + 3*(q*rd/math.pi)**2))
    def e_s(r,r_j,rd_j):
        return 1.0/(1 + pow(10,-g(rd_j)*(r - r_j)/400))

    for p,r,rd in winners:
        e = e_s(w_ensemble, l_ensemble, l_rd)
        dsq = 1.0/(((q*g(l_rd))**2)*e*(1-e))

        recip = 1.0/(1.0/(rd*rd) + 1.0/dsq)
        diff = q*recip*g(l_rd)*(1-e)

        if w_solo:
            p.rating = r + diff
            p.rd = math.sqrt(recip)
            if(p.rating > p.rating_peak and p.rd <= 110):
                p.rating_peak = p.rating
                p.rp_obtained = game_time
        else:
            p.team_rating = r + diff
            p.team_rd = math.sqrt(recip)
            if(p.team_rating > p.team_rating_peak and p.team_rd <= 110):
                p.team_rating_peak = p.team_rating
                p.trp_obtained = game_time

        changes.append((p,diff))


    for p,r,rd in losers:
        e = e_s(l_ensemble, w_ensemble, w_rd)
        dsq = 1.0/(((q*g(w_rd))**2)*e*(1-e))

        recip = 1.0/(1.0/(rd*rd) + 1.0/dsq)
        diff = q*recip*g(w_rd)*(-e)

        if l_solo:
            p.rating = r + diff
            p.rd = math.sqrt(recip)
            if(p.rating < p.rating_trough and p.rd <= 110):
                p.rating_trough = p.rating
                p.rt_obtained = game_time
        else:
            p.team_rating = r + diff
            p.team_rd = math.sqrt(recip)
            if(p.team_rating < p.team_rating_trough and p.team_rd <= 110):
                p.team_rating_trough = p.team_rating
                p.trt_obtained = game_time

        changes.append((p,diff))

    return changes

"""
def updateElo(ps, wins, game_time):
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
"""

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
        diff2b = 0,
        n_players = 0)

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
    game.n_players = len(ps)


    now = datetime.utcnow()
    newRatingPeriod(players, len(ps))
    changes = updateGlicko(ps, wins, now)
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
    leader_stats = [("rating","Rating",True), ("team_rating","Team Rating",True), ("win_pct","Win Percentage",True), ("streak","Win/Loss Streak",True)]
    if request.method == "GET":
        players=Player.query.all()
        leaders = {k : (n,sorted([(p.pid, p.name, vars(p)[k], p.rd, p.team_rd) for p in players],key = lambda tup: -1 if tup[2] is None else tup[2], reverse = b)) for k,n,b in leader_stats}
        leaders_list = list(leaders.items())
        leaders_list.sort(key = lambda tup: tup[1][0])
        return render_template("leaderboard.html", leaders=leaders_list)

@app.route('/hof', methods=['GET'])
def hof():
    record_stats = [("played","Most Games Played",max), ("rating_peak","Highest Rating Achieved",max), ("rating_trough","Lowest Rating Achieved",min), ("team_rating_peak","Highest Team Rating Achieved",max), ("team_rating_trough","Lowest Team Rating Achieved",min), ("streak_peak","Longest Win Streak",max), ("streak_trough","Longest Loss Streak",min)]
    if request.method == "GET":
        players=Player.query.all()
        vs = {n: f([(vars(p)[k],p.name) for p in players],key = lambda tup : tup[0]) for k,n,f in record_stats}
        vs_list = list(vs.items())
        vs_list.sort(key = lambda tup : [t[1] for t in record_stats].index(tup[0]))
        return render_template("hof.html", vs=vs_list)

@app.route('/games', methods=['GET'])
def games():
    gs = Game.query.order_by(Game.date.desc()).all()
    players = Player.query.all()
    name_dict = {p.pid : p.name for p in players}
    name_dict[0] = ""
    game_list = [(name_dict[g.player1a], g.diff1a, name_dict[g.player1b], g.diff1b, name_dict[g.player2a], g.diff2a, name_dict[g.player2b], g.diff2b, g.date, 2 - g.oneWin, g.id) for g in gs]

    return render_template("games.html",game_list=game_list)

@app.route('/history', methods=['GET'])
def history():
    gs = Game.query.order_by(Game.date).all()
    players = Player.query.all()
    name_dict = {p.pid : p.name for p in players}
    #should validate instead
    name_dict[0] = ""
    hist_dict = {p.name:([0],[1500]) for p in players}
    team_hist_dict = {p.name:([0],[1500]) for p in players}
    #should probably validate the below
    for n,g in enumerate(gs):
        teams = [[(g.player1a,g.diff1a),(g.player1b,g.diff1b)],[(g.player2a,g.diff2a),(g.player2b,g.diff2b)]]

        for i in range(2):
            solo = False
            #below won't work if we expand to larger teams
            if 0 in [tup[0] for tup in teams[i]]:
                solo = True
            for tup in teams[i]:
                pid = tup[0]
                if pid == 0:
                    continue
                p = name_dict[pid]
                if solo:
                    hist_dict[p][0].append(n+1)
                    hist_dict[p][1].append(hist_dict[p][1][-1]+tup[1])
                else:
                    team_hist_dict[p][0].append(n+1)
                    team_hist_dict[p][1].append(team_hist_dict[p][1][-1]+tup[1])

    hist_list = list(hist_dict.items())
    hist_list.sort(key = lambda t : t[0])
    n_games = [len(tup[0]) for _,tup in hist_list]

    team_hist_list = list(team_hist_dict.items())
    team_hist_list.sort(key = lambda t : t[0])
    team_n_games = [len(tup[0]) for _,tup in team_hist_list]

    def playerColour(i,n):
        seed = 0.8938123179670188
        incr = 1.0/n
        h,s,v = (seed + i*incr)%1 ,0.5,0.95
        h_i = int(h*6)
        f = h*6 - h_i
        p = v * (1 - s)
        q = v * (1 - f*s)
        t = v * (1 - (1 - f) * s)
        r, g, b = {
            0: (v, t, p),
            1: (q, v, p),
            2: (p, v, t),
            3: (p, q, v),
            4: (t, p, v),
            5: (v, p, q)
        }[h_i]
        return (int(r*256), int(g*256), int(b*256),1)

    histories = [("rating", "Rating", hist_list, len(hist_dict), n_games),("team_rating","Team Rating", team_hist_list, len(team_hist_dict), team_n_games)]


    return render_template("history.html",histories=histories, playerColour=playerColour)

