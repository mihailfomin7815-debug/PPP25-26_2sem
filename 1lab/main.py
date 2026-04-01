from abc import ABC, abstractmethod

WHITE, BLACK = 'white', 'black'
ICONS = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
    'C': '☩', 'c': '☨', 'A': '⚜', 'a': '⚝', 'Z': '⛨', 'z': '⛧',
}
KNIGHT_D = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
            (1, -2), (1, 2), (2, -1), (2, 1)]
ROOK_D = [(-1, 0), (1, 0), (0, -1), (0, 1)]
BISHOP_D = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
QUEEN_D = ROOK_D + BISHOP_D
opposite = lambda c: BLACK if c == WHITE else WHITE


class Position:
    __slots__ = ('row', 'col')

    def __init__(self, r, c):
        self.row, self.col = r, c

    def valid(self):
        return 0 <= self.row < 8 and 0 <= self.col < 8

    def shift(self, dr, dc):
        return Position(self.row + dr, self.col + dc)

    def __eq__(self, o):
        return isinstance(o, Position) and (self.row, self.col) == (o.row, o.col)

    def __hash__(self):
        return hash((self.row, self.col))

    def __repr__(self):
        return f"{chr(97 + self.col)}{self.row + 1}"

    @staticmethod
    def parse(s):
        if s and len(s) == 2 and s[0] in 'abcdefgh' and s[1] in '12345678':
            return Position(int(s[1]) - 1, ord(s[0]) - 97)


class Move:
    def __init__(self, **kw):
        d = dict(captured=None, castling_rook=None, rook_frm=None,
                 rook_to=None, ep_pos=None, promoted_to=None,
                 prev_ep=None, prev_moved=False, rook_prev_moved=False,
                 prev_halfmove=0)
        d.update(kw)
        self.__dict__.update(d)

    def __repr__(self):
        ic = ICONS.get(self.piece.symbol(), '?')
        cap = 'x' if self.captured else '-'
        p = f"={ICONS.get(self.promoted_to.symbol().upper(), '?')}" if self.promoted_to else ''
        c = (' O-O' if self.rook_frm.col == 7 else ' O-O-O') if self.castling_rook else ''
        e = ' e.p.' if self.ep_pos else ''
        return f"{ic}{self.frm}{cap}{self.to}{p}{c}{e}"


class Piece(ABC):
    value = 0
    _sym = ''
    _name = ''

    def __init__(self, color, pos):
        self.color, self.pos, self.moved = color, pos, False

    def symbol(self):
        return self._sym.upper() if self.color == WHITE else self._sym.lower()

    def name(self):
        return self._name

    @abstractmethod
    def pseudo_moves(self, b): ...

    def icon(self):
        return ICONS.get(self.symbol(), self.symbol())

    def legal_moves(self, b):
        return [p for p in self.pseudo_moves(b) if b.move_legal(self, p)]

    def attack_moves(self, b):
        return self.pseudo_moves(b)

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
        return [p for dr, dc in deltas for p in [self.pos.shift(dr, dc)]
                if p.valid() and (b.at(p) is None or b.at(p).color != self.color)]

    def _combined(self, b, sd, jd):
        seen, res = set(), []
        for p in self._slide(b, sd) + self._jumps(b, jd):
            if p not in seen:
                seen.add(p)
                res.append(p)
        return res

    def __repr__(self):
        return f"{self.icon()}({self.pos})"


class Korolj(Piece):
    _sym, _name = 'K', 'Король'

    def attack_moves(self, b):
        return self._jumps(b, QUEEN_D)

    def pseudo_moves(self, b):
        moves = self._jumps(b, QUEEN_D)
        if self.moved or b.attacked(self.pos, opposite(self.color)):
            return moves
        r = self.pos.row
        for rc, kdc in [(7, 2), (0, -2)]:
            rk = b.at(Position(r, rc))
            if not (rk and isinstance(rk, Ladja) and not rk.moved
                    and rk.color == self.color):
                continue
            lo, hi = min(rc, self.pos.col) + 1, max(rc, self.pos.col)
            if not all(b.at(Position(r, c)) is None for c in range(lo, hi)):
                continue
            step = 1 if kdc > 0 else -1
            if all(not b.attacked(Position(r, self.pos.col + step * i),
                                  opposite(self.color)) for i in range(1, 3)):
                moves.append(Position(r, self.pos.col + kdc))
        return moves


class Ferzj(Piece):
    _sym, _name, value = 'Q', 'Ферзь', 9

    def pseudo_moves(self, b):
        return self._slide(b, QUEEN_D)


class Ladja(Piece):
    _sym, _name, value = 'R', 'Ладья', 5

    def pseudo_moves(self, b):
        return self._slide(b, ROOK_D)


class Slon(Piece):
    _sym, _name, value = 'B', 'Слон', 3

    def pseudo_moves(self, b):
        return self._slide(b, BISHOP_D)


class Konj(Piece):
    _sym, _name, value = 'N', 'Конь', 3

    def pseudo_moves(self, b):
        return self._jumps(b, KNIGHT_D)


class Peshka(Piece):
    _sym, _name, value = 'P', 'Пешка', 1

    @property
    def dr(self):
        return 1 if self.color == WHITE else -1

    @property
    def start_row(self):
        return 1 if self.color == WHITE else 6

    @property
    def promo_row(self):
        return 7 if self.color == WHITE else 0

    def pseudo_moves(self, b):
        m, d = [], self.dr
        one = self.pos.shift(d, 0)
        if one.valid() and not b.at(one):
            m.append(one)
            two = self.pos.shift(2 * d, 0)
            if self.pos.row == self.start_row and not b.at(two):
                m.append(two)
        for dc in (-1, 1):
            cp = self.pos.shift(d, dc)
            if cp.valid():
                t = b.at(cp)
                if (t and t.color != self.color) or cp == b.ep_target:
                    m.append(cp)
        return m

    def attack_moves(self, b):
        return [p for dc in (-1, 1)
                for p in [self.pos.shift(self.dr, dc)] if p.valid()]


class Knjazj(Piece):
    _sym, _name, value = 'C', 'Князь', 8

    def pseudo_moves(self, b):
        return self._combined(b, ROOK_D, KNIGHT_D)


class Bojarin(Piece):
    _sym, _name, value = 'A', 'Боярин', 6

    def pseudo_moves(self, b):
        return self._combined(b, BISHOP_D, KNIGHT_D)


class Naezdnica(Piece):
    _sym, _name, value = 'Z', 'Наездница', 12

    def pseudo_moves(self, b):
        return self._combined(b, QUEEN_D, KNIGHT_D)


class Board:
    def __init__(self):
        self.grid = [[None] * 8 for _ in range(8)]
        self.pieces, self.ep_target = [], None

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

    def mv(self, pc, frm, to):
        self.grid[frm.row][frm.col] = None
        self.grid[to.row][to.col] = pc
        pc.pos = to

    def by_color(self, c):
        return [p for p in self.pieces if p.color == c]

    def king(self, c):
        return next((p for p in self.pieces
                     if isinstance(p, Korolj) and p.color == c), None)

    def attacked(self, pos, by):
        return any(pos in p.attack_moves(self) for p in self.by_color(by))

    def in_check(self, c):
        k = self.king(c)
        return k is not None and self.attacked(k.pos, opposite(c))

    def move_legal(self, piece, to):
        frm, cap = piece.pos, self.at(to)
        self.grid[frm.row][frm.col] = None
        self.grid[to.row][to.col] = piece
        piece.pos = to
        if cap and cap in self.pieces:
            self.pieces.remove(cap)
        ep_rm = None
        if isinstance(piece, Peshka) and to == self.ep_target and not cap:
            ep_p = Position(frm.row, to.col)
            ep_rm = self.grid[ep_p.row][ep_p.col]
            if ep_rm:
                self.grid[ep_p.row][ep_p.col] = None
                if ep_rm in self.pieces:
                    self.pieces.remove(ep_rm)
        ok = not self.in_check(piece.color)
        piece.pos = frm
        self.grid[frm.row][frm.col] = piece
        self.grid[to.row][to.col] = cap
        if cap and cap not in self.pieces:
            self.pieces.append(cap)
        if ep_rm:
            self.grid[frm.row][to.col] = ep_rm
            if ep_rm not in self.pieces:
                self.pieces.append(ep_rm)
        return ok

    def has_moves(self, c):
        return any(p.legal_moves(self) for p in self.by_color(c))

    def threatened(self, c):
        return [p for p in self.by_color(c) if self.attacked(p.pos, opposite(c))]

    def material(self, c):
        return sum(p.value for p in self.by_color(c))

    def setup(self, custom=False):
        row = ([Ladja, Bojarin, Slon, Naezdnica, Korolj, Slon, Knjazj, Ladja]
               if custom else
               [Ladja, Konj, Slon, Ferzj, Korolj, Slon, Konj, Ladja])
        for col, cls in enumerate(row):
            self.put(cls(WHITE, Position(0, col)))
            self.put(cls(BLACK, Position(7, col)))
        for col in range(8):
            self.put(Peshka(WHITE, Position(1, col)))
            self.put(Peshka(BLACK, Position(6, col)))


class Game:
    PROMO = {'q': Ferzj, 'r': Ladja, 'b': Slon, 'n': Konj,
             'c': Knjazj, 'a': Bojarin, 'z': Naezdnica}

    def __init__(self, custom=False):
        self.board = Board()
        self.board.setup(custom)
        self.turn, self.history = WHITE, []
        self.over, self.result, self.halfmove = False, '', 0

    def do_move(self, piece, to, promo='q'):
        b = self.board
        frm, cap = piece.pos, b.at(to)
        kw = dict(piece=piece, frm=frm, to=to, prev_moved=piece.moved,
                  prev_ep=b.ep_target, prev_halfmove=self.halfmove)
        if isinstance(piece, Korolj) and abs(to.col - frm.col) == 2:
            rc = 7 if to.col > frm.col else 0
            rf = Position(frm.row, rc)
            rt = Position(frm.row, 5 if rc == 7 else 3)
            rook = b.at(rf)
            kw.update(castling_rook=rook, rook_frm=rf, rook_to=rt,
                      rook_prev_moved=rook.moved)
            b.mv(rook, rf, rt)
            rook.moved = True
        if isinstance(piece, Peshka) and to == b.ep_target and not cap:
            ep = Position(frm.row, to.col)
            cap = b.rm(ep)
            kw['ep_pos'] = ep
        if cap and not kw.get('ep_pos'):
            b.rm(to)
        kw['captured'] = cap
        b.mv(piece, frm, to)
        piece.moved = True
        self.halfmove = 0 if isinstance(piece, Peshka) or cap else self.halfmove + 1
        b.ep_target = None
        if isinstance(piece, Peshka) and abs(to.row - frm.row) == 2:
            b.ep_target = Position((frm.row + to.row) // 2, to.col)
        if isinstance(piece, Peshka) and to.row == piece.promo_row:
            cls = self.PROMO.get(promo.lower(), Ferzj)
            np = cls(piece.color, to)
            np.moved = True
            b.rm(to)
            b.put(np)
            kw['promoted_to'] = np
        self.history.append(Move(**kw))
        self.turn = opposite(self.turn)
        self._check_end()
        return self.history[-1]

    def undo(self, n=1):
        undone = []
        for _ in range(n):
            if not self.history:
                break
            m = self.history.pop()
            self.over, self.result = False, ''
            b = self.board
            if m.promoted_to:
                b.rm(m.to)
                b.put(m.piece)
                m.piece.pos = m.to
            b.mv(m.piece, m.to, m.frm)
            m.piece.moved = m.prev_moved
            if m.castling_rook:
                b.mv(m.castling_rook, m.rook_to, m.rook_frm)
                m.castling_rook.moved = m.rook_prev_moved
            if m.captured:
                rp = m.ep_pos or m.to
                m.captured.pos = rp
                b.grid[rp.row][rp.col] = m.captured
                if m.captured not in b.pieces:
                    b.pieces.append(m.captured)
            b.ep_target, self.halfmove = m.prev_ep, m.prev_halfmove
            self.turn = opposite(self.turn)
            undone.append(m)
        return undone

    def _check_end(self):
        if not self.board.has_moves(self.turn):
            self.over = True
            self.result = (
                f"Мат! Победа {'белых' if self.turn == BLACK else 'чёрных'}!"
                if self.board.in_check(self.turn) else 'Пат! Ничья.')
        elif self.halfmove >= 100:
            self.over, self.result = True, 'Ничья по правилу 50 ходов.'
        elif self._insufficient():
            self.over, self.result = True, 'Ничья — недостаточно материала.'

    def _insufficient(self):
        w = [p for p in self.board.by_color(WHITE) if not isinstance(p, Korolj)]
        bl = [p for p in self.board.by_color(BLACK) if not isinstance(p, Korolj)]
        if not w and not bl:
            return True
        for a, o in [(w, bl), (bl, w)]:
            if not o and len(a) == 1 and isinstance(a[0], (Slon, Konj)):
                return True
        return (len(w) == 1 and len(bl) == 1
                and isinstance(w[0], Slon) and isinstance(bl[0], Slon)
                and (w[0].pos.row + w[0].pos.col) % 2
                == (bl[0].pos.row + bl[0].pos.col) % 2)


def render(board, moves=None, threats=None, check_king=None):
    ms, ts = set(moves or []), {p.pos for p in (threats or [])}
    ck = check_king.pos if check_king else None
    print('\n    a  b  c  d  e  f  g  h')
    print('  +' + '---' * 8 + '+')
    for row in range(7, -1, -1):
        cells = []
        for col in range(8):
            pos = Position(row, col)
            p = board.at(pos)
            if pos == ck:
                cells.append(f'!{p.icon()}!')
            elif pos in ms and p:
                cells.append(f'[{p.icon()}]')
            elif pos in ms:
                cells.append(' * ')
            elif pos in ts:
                cells.append(f'#{p.icon()}#')
            elif p:
                cells.append(f' {p.icon()} ')
            else:
                cells.append(' . ' if (row + col) % 2 == 0 else ' - ')
        print(f" {row + 1}|{''.join(cells)}|{row + 1}")
    print('  +' + '---' * 8 + '+')
    print('    a  b  c  d  e  f  g  h')
    diff = board.material(WHITE) - board.material(BLACK)
    if diff:
        print(f"  Материал: {'белые' if diff > 0 else 'чёрные'} +{abs(diff)}")
    print()


class App:
    def __init__(self):
        self.game = None

    def start(self):
        print('   ШАХМАТЫ   ' )
        print(' 1 - Стандартные\n 2 - С новыми фигурами')
        self.game = Game(custom=(input(' Выбор [1]: ').strip() == '2'))
        print('\nКоманды: e2 e4 | select e2 | undo [N] | '
              'threats | history | material | help | quit\n')
        self._loop()

    def _loop(self):
        g = self.game
        while not g.over:
            ck = g.board.king(g.turn) if g.board.in_check(g.turn) else None
            th = g.board.threatened(g.turn)
            render(g.board, threats=th, check_king=ck)
            side = 'Белые' if g.turn == WHITE else 'Чёрные'
            if ck:
                print('  ШАХ!')
            if th:
                print('  Под боем: ' + ', '.join(
                    f'{p.icon()} {p.name()}({p.pos})' for p in th))
            cmd = input(f'  [{side}, ход {len(g.history) // 2 + 1}]: ').strip()
            if not cmd:
                continue
            if cmd == 'quit':
                print('  Выход.')
                return
            if cmd == 'help':
                print('  e2 e4 | select e2 | undo [N] | '
                      'threats | history | material | quit')
            elif cmd == 'threats':
                for c in (WHITE, BLACK):
                    t = g.board.threatened(c)
                    nm = 'Белые' if c == WHITE else 'Чёрные'
                    print(f"  {nm}: " + (', '.join(
                        f'{p.icon()} {p.name()}({p.pos})' for p in t) or 'нет угроз'))
            elif cmd == 'history':
                if not g.history:
                    print('  Пусто.')
                for i, m in enumerate(g.history, 1):
                    print(f"  {(i + 1) // 2}.{'Б' if i % 2 else 'Ч'} {m}")
            elif cmd == 'material':
                print(f'  Белые: {g.board.material(WHITE)} | '
                      f'Чёрные: {g.board.material(BLACK)}')
            elif cmd.startswith('undo'):
                pts = cmd.split()
                n = int(pts[1]) if len(pts) > 1 and pts[1].isdigit() else 1
                ud = g.undo(n)
                for m in ud:
                    print(f'   Откат: {m}')
                if not ud:
                    print('  Нечего откатывать.')
            elif cmd.startswith('select'):
                self._select(cmd)
            else:
                self._move(cmd)
        ck = g.board.king(g.turn) if g.board.in_check(g.turn) else None
        render(g.board, check_king=ck)
        print(f'   {g.result} ')

    def _select(self, cmd):
        pts = cmd.split()
        if len(pts) != 2:
            print('  Формат: select e2')
            return
        pos = Position.parse(pts[1])
        if not pos:
            print('  Неверная клетка.')
            return
        p = self.game.board.at(pos)
        if not p or p.color != self.game.turn:
            print('  Клетка пуста.' if not p else '  Не ваша фигура.')
            return
        lm = p.legal_moves(self.game.board)
        print(f"  {p.icon()} {p.name()}: "
              f"{', '.join(str(m) for m in lm) or 'нет ходов'}")
        render(self.game.board, moves=lm)

    def _move(self, cmd):
        pts = cmd.split()
        if len(pts) < 2:
            print("  Формат: e2 e4")
            return
        f, t = Position.parse(pts[0]), Position.parse(pts[1])
        if not f or not t:
            print('  Неверная нотация.')
            return
        p = self.game.board.at(f)
        if not p or p.color != self.game.turn:
            print(f'  На {f} нет фигуры.' if not p else '  Не ваша фигура.')
            return
        lm = p.legal_moves(self.game.board)
        if t not in lm:
            print(f"  Нельзя! Можно: {', '.join(str(m) for m in lm) or 'нет'}")
            return
        promo = 'q'
        if isinstance(p, Peshka) and t.row == p.promo_row:
            opts = ' '.join(f"{k}={ICONS.get(k.upper(), k)}" for k in Game.PROMO)
            print(f'  Превращение: {opts}')
            promo = input('  Выбор [q]: ').strip() or 'q'
            if promo not in Game.PROMO:
                promo = 'q'
        print(f'  {self.game.do_move(p, t, promo)}')


if __name__ == '__main__':
    App().start()
