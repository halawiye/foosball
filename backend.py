from datetime import datetime
from flask_app import db, Player, Game, updateIndividual, updateGlicko, newRatingPeriod

def newPlayer(nom):
    epoch = datetime.utcfromtimestamp(0)
    player = Player(
        name = nom,
        played = 0,
        wins = 0,
        losses = 0,
        differential = 0,
        win_pct = None,
        streak = 0,
        rating = 1500,
        team_rating = 1500,
        rd = 350,
        team_rd = 350,
        tau = 0.06,
        team_tau = 0.06,
        streak_peak = 0,
        streak_trough = 0,
        rating_peak = 1500,
        team_rating_peak = 1500,
        rating_trough = 1500,
        team_rating_trough = 1500,
        differential_peak = 0,
        differential_trough = 0,
        sp_obtained = epoch,
        st_obtained = epoch,
        rp_obtained = epoch,
        trp_obtained = epoch,
        rt_obtained = epoch,
        trt_obtained = epoch,
        dp_obtained = epoch,
        dt_obtained = epoch)
    db.session.add(player)
    db.session.commit()


def recalculate():
    players = Player.query.all()
    epoch = datetime.utcfromtimestamp(0)
    for p in players:
        p.played = 0
        p.wins = 0
        p.losses = 0
        p.differential = 0
        p.win_pct = None
        p.streak = 0
        p.rating = 1500
        p.team_rating = 1500
        p.rd = 350
        p.team_rd = 350
        p.tau = 0.06
        p.team_tau = 0.06
        p.streak_peak = 0
        p.streak_trough = 0
        p.rating_peak = 1500
        p.team_rating_peak = 1500
        p.rating_trough = 1500
        p.team_rating_trough = 1500
        p.differential_peak = 0
        p.differential_trough = 0
        p.sp_obtained = epoch
        p.st_obtained = epoch
        p.rp_obtained = epoch
        p.trp_obtained = epoch
        p.rt_obtained = epoch
        p.trt_obtained = epoch
        p.dp_obtained = epoch
        p.dt_obtained = epoch
        p.last_played = None


    games = Game.query.order_by(Game.date).all()
    for game in games:
        ids = [game.player1a, game.player1b, game.player2a, game.player2b]
        teams = [[game.player1a,game.player1b],[game.player2a,game.player2b]]

        ps = []
        wins = []

        for i in range(2):
            for pid in teams[i]:
                p = Player.query.get(pid)
                if p is None:
                    continue
                ps.append(p)
                if ((i == 0 and game.oneWin) or (i == 1 and not game.oneWin)):
                    wins.append(1)
                else:
                    wins.append(0)

        game.n_players = len(ps)

        newRatingPeriod(players, len(ps))
        changes = updateGlicko(ps, wins, game.date)
        for i in range(len(ps)):
            updateIndividual(ps[i],wins[i], game.date)

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

        db.session.commit()
