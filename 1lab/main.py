from abc import ABC, abstractmethod

WHITE, BLACK = 'white', 'black'


def opposite(color):
    return BLACK if color == WHITE else WHITE


class Position:
    def __init__(self, row, col):
        self.row = row
        self.col = col

    def valid(self):
        return 0 <= self.row < 8 and 0 <= self.col < 8

    def shift(self, dr, dc):
        return Position(self.row + dr, self.col + dc)

    def __eq__(self, o):
        return isinstance(o, Position) and self.row == o.row and self.col == o.col

    def __hash__(self):
        return hash((self.row, self.col))

    def __repr__(self):
        return f"{chr(97 + self.col)}{self.row + 1}"

    @staticmethod
    def parse(s):
        if len(s) != 2 or s[0] not in 'abcdefgh' or s[1] not in '12345678':
            return None
        return Position(int(s[1]) - 1, ord(s[0]) - 97)


class Move:
    def __init__(self, **kw):
        self.piece = kw['piece']
        self.frm = kw['frm']
        self.to = kw['to']
        self.captured = kw.get('captured')
        self.castling_rook = kw.get('castling_rook')
        self.rook_frm = kw.get('rook_frm')
        self.rook_to = kw.get('rook_to')
        self.ep_pos = kw.get('ep_pos')
        self.promoted_to = kw.get('promoted_to')
        self.prev_moved = kw.get('prev_moved', False)
        self.prev_ep = kw.get('prev_ep')

    def __repr__(self):
        c = "x" if self.captured else "-"
        return f"{self.piece.symbol()}{self.frm}{c}{self.to}"


class Piece(ABC):
    def __init__(self, color, pos):
        self.color = color
        self.pos = pos
        self.moved = False

    @abstractmethod
    def symbol(self): ...

    @abstractmethod
    def name(self): ...

    @abstractmethod
    def pseudo_moves(self, b): ...

    def legal_moves(self, b):
        return [p for p in self.pseudo_moves(b) if b.move_legal(self, p)]

    def _slide(self, b, dirs):
        res = []
        for dr, dc in dirs:
            p = self.pos.shift(dr, dc)
            while p.valid():
                t = b.at(p)
                if t is None:
                    res.append(p)
                elif t.color != self.color:
                    res.append(p)
                    break
                else:
                    break
                p = p.shift(dr, dc)
        return res

    def _jumps(self, b, deltas):
        res = []
        for dr, dc in deltas:
            p = self.pos.shift(dr, dc)
            if p.valid():
                t = b.at(p)
                if t is None or t.color != self.color:
                    res.append(p)
        return res

    def __repr__(self):
        return f"{self.symbol()}({self.pos})"
 
    def attack_moves(self, b):
        return self.pseudo_moves(b)


KNIGHT_D = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
            (1, -2), (1, 2), (2, -1), (2, 1)]
ROOK_D = [(-1, 0), (1, 0), (0, -1), (0, 1)]
BISHOP_D = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
QUEEN_D = ROOK_D + BISHOP_D


class Korolj(Piece):

    def symbol(self):
        return 'K' if self.color == WHITE else 'k'

    def name(self):
        return "Король"

    def attack_moves(self, b):
        return self._jumps(b, QUEEN_D)

    def pseudo_moves(self, b):
        moves = self._jumps(b, QUEEN_D)
        if self.moved:
            return moves
        if b.attacked(self.pos, opposite(self.color)):
            return moves
        
        for rc, pcols, kdc in [(7, range(self.pos.col + 1, 7), 2),
                                (0, range(1, self.pos.col), -2)]:
            r = b.at(Position(self.pos.row, rc))
            if r and isinstance(r, Ladja) and not r.moved and r.color == self.color:
                if all(b.at(Position(self.pos.row, c)) is None for c in pcols):
                    step = 1 if kdc > 0 else -1
                    if all(not b.attacked(Position(self.pos.row, self.pos.col + step * i),
                                          opposite(self.color)) for i in range(1, 3)):
                        moves.append(Position(self.pos.row, self.pos.col + kdc))
        return moves


class Ferzj(Piece):
    def symbol(self):
        return 'Q' if self.color == WHITE else 'q'

    def name(self):
        return "Ферзь"

    def pseudo_moves(self, b):
        return self._slide(b, QUEEN_D)


class Ladja(Piece):
    def symbol(self):
        return 'R' if self.color == WHITE else 'r'

    def name(self):
        return "Ладья"

    def pseudo_moves(self, b):
        return self._slide(b, ROOK_D)


class Slon(Piece):
    def symbol(self):
        return 'B' if self.color == WHITE else 'b'

    def name(self):
        return "Слон"

    def pseudo_moves(self, b):
        return self._slide(b, BISHOP_D)


class Konj(Piece):
    def symbol(self):
        return 'N' if self.color == WHITE else 'n'

    def name(self):
        return "Конь"

    def pseudo_moves(self, b):
        return self._jumps(b, KNIGHT_D)


class Peshka(Piece):
    def symbol(self):
        return 'P' if self.color == WHITE else 'p'

    def name(self):
        return "Пешка"

    @property
    def dr(self):
        return 1 if self.color == WHITE else -1

    @property
    def promo_row(self):
        return 7 if self.color == WHITE else 0

    def pseudo_moves(self, b):
        m, d, start = [], self.dr, (1 if self.color == WHITE else 6)
        one = self.pos.shift(d, 0)
        if one.valid() and not b.at(one):
            m.append(one)
            two = self.pos.shift(2 * d, 0)
            if self.pos.row == start and two.valid() and not b.at(two):
                m.append(two)
        for dc in [-1, 1]:
            cp = self.pos.shift(d, dc)
            if cp.valid():
                t = b.at(cp)
                if (t and t.color != self.color) or cp == b.ep_target:
                    m.append(cp)
        return m
    
    def attack_moves(self, b):
        res = []
        for dc in [-1, 1]:
            p = self.pos.shift(self.dr, dc)
            if p.valid():
                res.append(p)
        return res


class Knjazj(Piece):
    """Князь: ходит как ладья + конь"""
    def symbol(self):
        return 'C' if self.color == WHITE else 'c'

    def name(self):
        return "Князь"

    def pseudo_moves(self, b):
        return self._slide(b, ROOK_D) + self._jumps(b, KNIGHT_D)


class Bojarin(Piece):
    """Боярин: ходит как слон + конь"""
    def symbol(self):
        return 'A' if self.color == WHITE else 'a'

    def name(self):
        return "Боярин"

    def pseudo_moves(self, b):
        return self._slide(b, BISHOP_D) + self._jumps(b, KNIGHT_D)


class Naezdnica(Piece):
    """Наездница: ходит как ферзь + конь"""
    def symbol(self):
        return 'Z' if self.color == WHITE else 'z'

    def name(self):
        return "Наездница"

    def pseudo_moves(self, b):
        return self._slide(b, QUEEN_D) + self._jumps(b, KNIGHT_D)


class Board:
    def __init__(self):
        self.grid = [[None] * 8 for _ in range(8)]
        self.pieces = []
        self.ep_target = None

    def put(self, p):
        self.grid[p.pos.row][p.pos.col] = p
        self.pieces.append(p)

    def rm(self, pos):
        p = self.grid[pos.row][pos.col]
        if p:
            self.grid[pos.row][pos.col] = None
            if p in self.pieces:
                self.pieces.remove(p)
        return p

    def at(self, pos):
        return self.grid[pos.row][pos.col] if pos.valid() else None

    def mv(self, piece, frm, to):
        self.grid[frm.row][frm.col] = None
        self.grid[to.row][to.col] = piece
        piece.pos = to

    def by_color(self, c):
        return [p for p in self.pieces if p.color == c]

    def king(self, c):
        return next((p for p in self.pieces if isinstance(p, Korolj) and p.color == c), None)

    def attacked(self, pos, by):
        return any(pos in p.attack_moves(self) for p in self.by_color(by))

    def in_check(self, c):
        k = self.king(c)
        return k is not None and self.attacked(k.pos, opposite(c))

    def move_legal(self, piece, to):
        frm = piece.pos
        cap = self.at(to)
        self.grid[frm.row][frm.col] = None
        self.grid[to.row][to.col] = piece
        piece.pos = to
        if cap and cap in self.pieces:
            self.pieces.remove(cap)

        ep_rm = None
        if isinstance(piece, Peshka) and to == self.ep_target and cap is None:
            ep_p = Position(frm.row, to.col)
            ep_rm = self.grid[ep_p.row][ep_p.col]
            self.grid[ep_p.row][ep_p.col] = None
            if ep_rm and ep_rm in self.pieces:
                self.pieces.remove(ep_rm)

        ok = not self.in_check(piece.color)

        piece.pos = frm
        self.grid[frm.row][frm.col] = piece
        self.grid[to.row][to.col] = cap
        if cap and cap not in self.pieces:
            self.pieces.append(cap)
        if ep_rm:
            ep_p = Position(frm.row, to.col)
            self.grid[ep_p.row][ep_p.col] = ep_rm
            if ep_rm not in self.pieces:
                self.pieces.append(ep_rm)
        return ok

    def has_moves(self, c):
        return any(p.legal_moves(self) for p in self.by_color(c))

    def threatened(self, c):
        return [p for p in self.by_color(c) if self.attacked(p.pos, opposite(c))]

    def setup(self, custom=False):
        if custom:
            row = [Ladja, Bojarin, Slon, Naezdnica, Korolj, Slon, Knjazj, Ladja]
        else:
            row = [Ladja, Konj, Slon, Ferzj, Korolj, Slon, Konj, Ladja]
        for col, cls in enumerate(row):
            self.put(cls(WHITE, Position(0, col)))
            self.put(cls(BLACK, Position(7, col)))
        for col in range(8):
            self.put(Peshka(WHITE, Position(1, col)))
            self.put(Peshka(BLACK, Position(6, col)))


class Game:
    PROMO = {
        'q': Ferzj, 'r': Ladja, 'b': Slon, 'n': Konj,
        'c': Knjazj, 'a': Bojarin, 'z': Naezdnica
    }

    def __init__(self, custom=False):
        self.board = Board()
        self.board.setup(custom)
        self.turn = WHITE
        self.history = []
        self.over = False
        self.result = ""

    def do_move(self, piece, to, promo='q'):
        frm = piece.pos
        cap = self.board.at(to)
        kw = dict(piece=piece, frm=frm, to=to,
                  prev_moved=piece.moved, prev_ep=self.board.ep_target)

        if isinstance(piece, Korolj) and abs(to.col - frm.col) == 2:
            rc = 7 if to.col > frm.col else 0
            rf = Position(frm.row, rc)
            rt = Position(frm.row, 5 if rc == 7 else 3)
            rook = self.board.at(rf)
            self.board.mv(rook, rf, rt)
            rook.moved = True
            kw.update(castling_rook=rook, rook_frm=rf, rook_to=rt)

        # Взятие на проходе
        if isinstance(piece, Peshka) and to == self.board.ep_target and cap is None:
            ep = Position(frm.row, to.col)
            cap = self.board.rm(ep)
            kw['ep_pos'] = ep

        if cap and not kw.get('ep_pos'):
            self.board.rm(to)
        kw['captured'] = cap

        self.board.mv(piece, frm, to)
        piece.moved = True

        self.board.ep_target = None
        if isinstance(piece, Peshka) and abs(to.row - frm.row) == 2:
            self.board.ep_target = Position((frm.row + to.row) // 2, to.col)

        if isinstance(piece, Peshka) and to.row == piece.promo_row:
            cls = self.PROMO.get(promo.lower(), Ferzj)
            new_p = cls(piece.color, to)
            new_p.moved = True
            self.board.rm(to)
            self.board.put(new_p)
            kw['promoted_to'] = new_p

        move = Move(**kw)
        self.history.append(move)
        self.turn = opposite(self.turn)
        self._check_end()
        return move

    def undo(self):
        if not self.history:
            return None
        m = self.history.pop()
        self.over, self.result = False, ""

        if m.promoted_to:
            self.board.rm(m.to)
            self.board.put(m.piece)
            m.piece.pos = m.to

        self.board.mv(m.piece, m.to, m.frm)
        m.piece.moved = m.prev_moved

        if m.castling_rook:
            self.board.mv(m.castling_rook, m.rook_to, m.rook_frm)
            m.castling_rook.moved = False

        if m.captured:
            rp = m.ep_pos if m.ep_pos else m.to
            m.captured.pos = rp
            self.board.grid[rp.row][rp.col] = m.captured
            if m.captured not in self.board.pieces:
                self.board.pieces.append(m.captured)

        self.board.ep_target = m.prev_ep
        self.turn = opposite(self.turn)
        return m

    def _check_end(self):
        if not self.board.has_moves(self.turn):
            self.over = True
            if self.board.in_check(self.turn):
                w = "белых" if self.turn == BLACK else "чёрных"
                self.result = f"Мат! Победа {w}!"
            else:
                self.result = "Пат! Ничья."


def render(b, moves=None, threats=None, check_king=None):
    ms = set(moves) if moves else set()
    ts = {p.pos for p in threats} if threats else set()
    ck = check_king.pos if check_king else None

    print()
    print("    a  b  c  d  e  f  g  h")
    for row in range(7, -1, -1):
        line = f" {row + 1} "
        for col in range(8):
            pos = Position(row, col)
            p = b.at(pos)
            light = (row + col) % 2 == 0

            if pos == ck:
                ch = f"!{p.symbol()}!"
            elif pos in ms and p:
                ch = f"[{p.symbol()}]"
            elif pos in ms:
                ch = " . "
            elif pos in ts:
                ch = f"*{p.symbol()}*"
            elif p:
                ch = f" {p.symbol()} "
            else:
                ch = " - " if light else " . "

            line += ch
        print(f"{line}  {row + 1}")
    print("    a  b  c  d  e  f  g  h")
    print()


class App:
    def __init__(self):
        self.game = None

    def start(self):
        print("=" * 40)
        print("ШАХМАТЫ")
        print("=" * 40)
        print(" 1 Стандартные  2 С новыми фигурами")
        choice = input(" Выбор: ").strip()
        self.game = Game(custom=(choice == '2'))
        print("Команды: e2 e4(сделать ход) | select e2(показать ходы фигуры) "
              "| undo(отмена хода) | threats(показать атакуемые фигуры) | quit(выход)")
        self._loop()

    def _loop(self):
        g = self.game
        while not g.over:
            ck = g.board.king(g.turn) if g.board.in_check(g.turn) else None
            th = g.board.threatened(g.turn)
            render(g.board, threats=th, check_king=ck)

            side = "Белые" if g.turn == WHITE else "Чёрные"
            if ck:
                print("ШАХ!")
            if th:
                info = ', '.join(f'{p.name()}({p.pos})' for p in th)
                print(f"Под боем: {info}")

            cmd = input(f"[{side}]: ").strip()
            if not cmd:
                continue
            if cmd == 'quit':
                return
            if cmd == 'undo':
                m = g.undo()
                if m:
                    print(f"Откат: {m}")
                else:
                    print("Нечего откатывать.")
                continue
            if cmd == 'threats':
                for c in [WHITE, BLACK]:
                    t = g.board.threatened(c)
                    n = "Белые" if c == WHITE else "Чёрные"
                    if t:
                        info = ', '.join(f'{p.name()}({p.pos})' for p in t)
                        print(f"{n}: {info}")
                    else:
                        print(f"{n}: нет")
                continue
            if cmd.startswith('select'):
                self._select(cmd)
                continue
            self._move(cmd)

        ck = g.board.king(g.turn) if g.board.in_check(g.turn) else None
        render(g.board, check_king=ck)
        print(f"  {g.result}")

    def _select(self, cmd):
        parts = cmd.split()
        if len(parts) != 2:
            print("Формат: select e2")
            return
        pos = Position.parse(parts[1])
        if not pos:
            print("Неверная клетка.")
            return
        p = self.game.board.at(pos)
        if not p or p.color != self.game.turn:
            print("Не ваша фигура.")
            return
        lm = p.legal_moves(self.game.board)
        if lm:
            print(f"{p.name()}: {', '.join(str(m) for m in lm)}")
        else:
            print(f"{p.name()}: нет ходов")
        render(self.game.board, moves=lm)

    def _move(self, cmd):
        parts = cmd.split()
        if len(parts) < 2:
            print("Формат: e2 e4")
            return
        f, t = Position.parse(parts[0]), Position.parse(parts[1])
        if not f or not t:
            print("Неверная нотация.")
            return
        p = self.game.board.at(f)
        if not p or p.color != self.game.turn:
            print("Не ваша фигура.")
            return
        lm = p.legal_moves(self.game.board)
        if t not in lm:
            if lm:
                info = ', '.join(str(m) for m in lm)
                print(f"Недопустимый ход! Можно: {info}")
            else:
                print("Недопустимый ход! Нет доступных ходов.")
            return
        promo = 'q'
        if isinstance(p, Peshka) and t.row == p.promo_row:
            print("Превращение: q/r/b/n/c/a/z")
            promo = input("Выбор: ").strip() or 'q'
        m = self.game.do_move(p, t, promo)
        print(f"OK: {m}")


if __name__ == "__main__":
    App().start()
