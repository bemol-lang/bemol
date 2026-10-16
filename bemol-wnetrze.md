# BEMOL ♭ — wnętrze języka

> Jak BEMOL działa „pod spodem”: tablice menedżera, liczenie adresów, optymalizacje kompilatora.
> Uzupełnienie dokumentu [**bemol-specyfikacja.md**](bemol-specyfikacja.md) · Status: **szkic roboczy** · ostatnia aktualizacja: 2026-10-16

Specyfikacja mówi, **co** programista pisze i co się stanie. Ten dokument mówi, **jak** to działa w środku. Programista BEMOL-a nie musi go znać, żeby pisać programy, ale im lepiej rozumie wnętrze języka, tym lepiej rozumie narzędzie, którym pracuje: wie, dlaczego `unsigned_16` jest szybsze od `unsigned_12`, ile kosztuje widok i dlaczego bloku z widokami nie da się zwolnić.

Dokument jest też instrukcją dla każdego, kto będzie pisał kompilator BEMOL-a.

**Zasada:** na zewnątrz proste dla człowieka, w środku optymalne dla maszyny.

---

## Spis treści

1. [Menedżer bloków](#1-menedżer-bloków)
2. [Zmienna `pointer` i droga do danych](#2-zmienna-pointer-i-droga-do-danych)
3. [Soczewki: obliczanie pozycji](#3-soczewki-obliczanie-pozycji)
4. [Struktury z polami bitowymi](#4-struktury-z-polami-bitowymi)
5. [Widoki krok po kroku](#5-widoki-krok-po-kroku)
6. [Odłamki w praktyce](#6-odłamki-w-praktyce)
7. [`PERSISTENT` w praktyce](#7-persistent-w-praktyce)
8. [Pliki mapowane](#8-pliki-mapowane)
9. [Optymalizacje kompilatora](#9-optymalizacje-kompilatora)
10. [Kompilacje cząstkowe i zależności](#10-kompilacje-cząstkowe-i-zależności)

---

## 1. Menedżer bloków

### Tablica przydziałów

Menedżer bloków to jedna **tablica dynamiczna**. Każdy wiersz (wpis) opisuje jeden blok pamięci albo jeden widok. **Numer wiersza jest identyfikatorem bloku.**

Wpis zajmuje **32 bajty**. Dostęp do wpisu nr `n`:

```
adres wpisu = początek tablicy + n × 32
```

Mnożenie przez 32 to przesunięcie bitowe o 5 pozycji, czyli jedna z najszybszych instrukcji procesora. W jednej linii pamięci podręcznej (64 bajty) mieszczą się dokładnie dwa wpisy.

### Wpis bajt po bajcie

```
przesunięcie:  0               8               16      20  22  24              32
               ├───────────────┼───────────────┼───────┼───┼───┼───────────────┤
zwykły blok:   │ adres         │ długość       │shares │flg│wid│ zarezerwowane │
widok (VIEW):  │ przesunięcie  │ długość       │shares │flg│ 0 │rodzic │ opis  │
               └───────────────┴───────────────┴───────┴───┴───┴───────┴───────┘
                 8 B             8 B             4 B    2 B 2 B  4 B     4 B
```

| Przesunięcie | Zwykły blok | Widok (`VIEW`) |
|---|---|---|
| 0 (8 B) | adres bloku w pamięci | przesunięcie widoku w rodzicu |
| 8 (8 B) | długość w bajtach | długość widoku w bajtach |
| 16 (4 B) | `.shares` | `.shares` widoku |
| 20 (2 B) | flagi (16 bitów) | flagi |
| 22 (2 B) | liczba widoków | 0 |
| 24 (4 B) | zarezerwowane | numer rodzica |
| 28 (4 B) | zarezerwowane | numer opisu prostokąta (0 = brak) |

O tym, jak czytać pola, decyduje flaga `VIEW` (bit 2).

### Flagi

```
bit:  15 14 13 12 11 10  9  8  7  6  5  4  3  2  1  0
      ─────────────────  ─────  ─  ─  ─  ─  ─  ─  ─  ─
           wolne        range PRD DBG ·  MW MP VW PE GL
                        Error
```

| Bit | Skrót | Flaga |
|---|---|---|
| 0 | GL | `GLOBAL` |
| 1 | PE | `PERSISTENT` |
| 2 | VW | `VIEW` |
| 3 | MP | `MAPPED` |
| 4 | MW | `MAPPED_WRITABLE` |
| 5 | · | zarezerwowany |
| 6 | DBG | `DEBUG_MEMORY_PATTERN` |
| 7 | PRD | `PRODUCTION_MEMORY_PATTERN` |
| 8–9 | rangeError | tryb: 0 = DEFAULT, 1 = CONTINUE, 2 = WARNING, 3 = HALT |
| 10–15 | — | wolne |

Odczyt trybu `rangeError` to jedna operacja: `(flagi >> 8) & 3`.

### Lista wolnych wpisów

Gdy blok zostaje zwolniony, jego numer trafia na listę wolnych wpisów. Następne `.new` bierze numer z tej listy, a dopiero gdy lista jest pusta, tablica rośnie o nowy wiersz. Dzięki temu tablica nie puchnie w programach, które tworzą i zwalniają bloki w pętli.

**Wpis jest wolny, gdy `.shares` = 0 i liczba widoków = 0.**

### Kiedy blok jest zwalniany

```
            .shares spada        liczba widoków spada
                 │                       │
                 └──────────┬────────────┘
                            ▼
              .shares = 0  i  liczba widoków = 0 ?
                    │                     │
                   tak                   nie
                    ▼                     ▼
          zwolnij pamięć bloku      blok zostaje
          numer → lista wolnych
```

Przykład: funkcja tworzy obraz, robi na nim widok `kafelek` i zwraca tylko widok. Po wyjściu z funkcji zmienna obrazu znika, więc `.shares` obrazu = 0, ale liczba widoków = 1. Blok zostaje, a widok dalej pracuje na danych. Gdy zniknie i widok, liczba widoków spada do 0 i dopiero wtedy pamięć obrazu jest zwalniana.

---

## 2. Zmienna `pointer` i droga do danych

Zmienna `pointer` w programie to **4 bajty: numer wpisu w menedżerze**. Nie przechowuje adresu.

Dostęp do `ptr.byte[5]`:

```
1. numer = ptr                       # np. 17
2. wpis  = tablica + 17 × 32
3. adres = wpis.adres                # odczyt 8 bajtów z wpisu
4. dane  = pamięć[adres + 5]
```

To o jeden odczyt więcej niż w C, gdzie wskaźnik od razu jest adresem. Zysk: gdy `.update` przenosi blok w inne miejsce, zmienia się tylko `wpis.adres`, a wszystkie zmienne (i widoki) od razu widzą nowy adres. Nie istnieją wskaźniki „donikąd”.

Koszt dodatkowego odczytu znika w pętlach dzięki optymalizacji z rozdziału 9: kompilator czyta adres raz przed pętlą.

---

## 3. Soczewki: obliczanie pozycji

### Soczewki o pełnych bajtach

```
pozycja w bajtach = n × rozmiar typu
```

| Zapis | Obliczenie | Bajt |
|---|---|---|
| `ptr.byte[7]` | 7 × 1 | 7 |
| `ptr.int[4]` | 4 × 4 | 16 |
| `ptr.Color[32]` | 32 × 10 | 320 |

Rozmiar typu jest stałą znaną podczas kompilacji, więc to jedno mnożenie (często zamieniane na przesunięcia bitowe).

### Soczewki bitowe (`.bit`, `unsigned_N`, `signed_N`)

Dla soczewki o szerokości N bitów:

```
pozycja w bitach = n × N
bajt startowy    = pozycja / 8
przesunięcie     = pozycja % 8
wartość          = (wczytane bajty >> przesunięcie) & maska N bitów
```

Przykład: `ptr.unsigned_12[3]`

```
pozycja w bitach = 3 × 12 = 36
bajt startowy    = 36 / 8 = 4
przesunięcie     = 36 % 8 = 4
wczytaj bajty 4 i 5 (16 bitów), przesuń w prawo o 4, zostaw 12 bitów (maska &FFFh)
```

Dlatego szerokości nienatywne są wolniejsze: zamiast jednej instrukcji odczytu potrzeba odczytu, przesunięcia i maski, a sąsiednie elementy dzielą bajty, co utrudnia instrukcje wektorowe.

---

## 4. Struktury z polami bitowymi

Pola struktury leżą jedno za drugim, bit przy bicie. Kompilator wylicza przesunięcie każdego pola podczas kompilacji.

```
Mix as STRUCT { aktywny as bit, wartosc as unsigned_16 }
```

| Pole | Bity w strukturze | Rozmiar |
|---|---|---|
| `aktywny` | 0 | 1 bit |
| `wartosc` | 1–16 | 16 bitów |
| wypełnienie | 17–23 | 7 bitów |

Razem 17 bitów, zaokrąglone do **3 bajtów**. Układ w pamięci (bajty od adresu 0):

```
bajt 0: [w6 w5 w4 w3 w2 w1 w0 A ]    A  = aktywny
bajt 1: [w14 ...            w7 ]    w0–w15 = wartosc
bajt 2: [ - - - - - - -   w15 ]    -  = wypełnienie
```

Odczyt `ptr.Mix[n].wartosc`:

```
początek elementu = n × 3 bajty
wczytaj 3 bajty od początku elementu
wartosc = (bajty >> 1) & &FFFFh
```

Każdy element `Mix` zaczyna się na granicy bajtu (dzięki zaokrągleniu rozmiaru), więc przejście do kolejnego elementu to zwykłe dodanie 3 do adresu.

---

## 5. Widoki krok po kroku

### Przykład 10 × 10 bajtów

Blok rodzica ma 100 bajtów, ułożonych jak obraz 10 × 10, gdzie **jeden piksel = jeden bajt**. Numer w polu to numer bajtu w bloku:

```
        x→  0   1   2   3   4   5   6   7   8   9
  y=0      00  01  02  03  04  05  06  07  08  09
  y=1      10  11  12  13  14  15  16  17  18  19
  y=2      20  21  22  23  24  25  26  27  28  29
  y=3      30  31 [32  33  34  35] 36  37  38  39
  y=4      40  41 [42  43  44  45] 46  47  48  49
  y=5      50  51 [52  53  54  55] 56  57  58  59
  y=6      60  61  62  63  64  65  66  67  68  69
  ...
```

Prostokąt w nawiasach: od x = 2, y = 3, szerokość 4, wysokość 3. Wiersz rodzica ma 10 bajtów, więc krok = 10:

```
kafelek = blok.viewRectangle[2, 3, 4, 3, 10]
```

### Tworzenie: co trafia do tabel

**Wpis widoku w menedżerze bloków:**

| Pole | Obliczenie | Wartość |
|---|---|---|
| przesunięcie | y × krok + x = 3 × 10 + 2 | **32** |
| długość | szerokość × wysokość = 4 × 3 | **12** |
| numer rodzica | numer bloku `blok` w menedżerze | np. 3 |
| numer opisu | wolny wiersz w tablicy opisów prostokątów | np. 7 |

Przy okazji liczba widoków we wpisie nr 3 (rodzica) rośnie o 1.

**Opis prostokąta nr 7 (16 bajtów):**

| Pole | Wartość |
|---|---|
| bajty wiersza | **4** |
| krok | **10** |

Przesunięcie 32 to lewy górny róg prostokąta. Liczba wierszy nie jest zapisywana: 12 / 4 = 3.

### Odczyt bajtu nr k widoku

Dla programu widok wygląda jak ciągły blok 12 bajtów (k = 0...11):

```
wiersz    = k / bajty wiersza
kolumna   = k % bajty wiersza
bajt      = przesunięcie + wiersz × krok + kolumna
adres     = adres rodzica + bajt
```

| k | wiersz | kolumna | bajt w rodzicu |
|---|---|---|---|
| 0 | 0 | 0 | 32 + 0 + 0 = **32** |
| 1 | 0 | 1 | **33** |
| 2 | 0 | 2 | **34** |
| 3 | 0 | 3 | **35** |
| 4 | 1 | 0 | 32 + 10 + 0 = **42** |
| 5 | 1 | 1 | **43** |
| 6 | 1 | 2 | **44** |
| 7 | 1 | 3 | **45** |
| 8 | 2 | 0 | 32 + 20 + 0 = **52** |
| 9 | 2 | 1 | **53** |
| 10 | 2 | 2 | **54** |
| 11 | 2 | 3 | **55** |

Wychodzą dokładnie bajty w nawiasach. `kafelek.byte[5]` to bajt 43 rodzica.

Gdy rodzic zostanie przeniesiony przez `.update`, żadna z tych liczb się nie zmienia. Zmienia się tylko adres we wpisie rodzica nr 3.

### Widok paskowy

Gdy numer opisu = 0 (`viewPortion`), nie ma wierszy:

```
adres = adres rodzica + przesunięcie + k
```

### Pętla po widoku prostokątnym

Dzielenie i reszta są potrzebne tylko przy dostępie w losowe miejsce. W pętli po całym widoku kompilator przechodzi wiersz po wierszu:

```
adres_wiersza = adres rodzica + przesunięcie
powtórz (liczba wierszy) razy:
    przetwórz (bajty wiersza) bajtów od adres_wiersza   # ciągły pasek: pełna prędkość, SIMD
    adres_wiersza = adres_wiersza + krok
```

Każdy wiersz to ciągły kawałek pamięci, więc instrukcje wektorowe działają w nim bez przeszkód.

### Spłaszczanie widoku widoku

Widok utworzony na widoku jest od razu zamieniany na widok bezpośrednio na blok źródłowy. Przykład dla widoków paskowych:

```
a = blok.viewPortion[100:500]     # przesunięcie 100 w bloku
b = a.viewPortion[20:50]          # przesunięcie 20 w widoku a

wpis b: rodzic = blok (nie a!), przesunięcie = 100 + 20 = 120, długość = 50
```

Dostęp do danych przez `b` to zawsze jeden poziom: wpis `b` → wpis bloku → adres. Liczba widoków rośnie we wpisie bloku źródłowego.

---

## 6. Odłamki w praktyce

Przykład: blok 1023 bajtów, odczyt `x as float` przez `ptr.float[255]` (pozycja 1020, potrzebne 4 bajty, istnieją 3):

```
1. x = 0                                   # cała zmienna docelowa wyzerowana
2. dostępne = długość - pozycja = 3        # bajty 1020, 1021, 1022
3. skopiuj 3 bajty do najmniej znaczącej części x
4. bajt najbardziej znaczący zostaje 0
5. reakcja według .rangeError (bity 8–9 flag)
```

Zapis w drugą stronę: z 4 bajtów wartości do bloku trafiają tylko 3 istniejące, czwarty jest odrzucany.

W pętli kompilator nie robi tego przy każdym elemencie: sprawdza zakres raz przed pętlą (rozdział 9), a ścieżkę z odłamkiem wykonuje tylko dla ostatniego, niepełnego elementu.

---

## 7. `PERSISTENT` w praktyce

```
FUNCTION przetwarzaj(): void
    PERSISTENT bufor as pointer
    bufor.new[4096]
    ...
przetwarzaj.end
```

1. **Pierwsze wywołanie:** menedżer przydziela wpis i ustawia w nim flagę `PERSISTENT` (bit 1). Numer wpisu kompilator zapamiętuje w ukrytej zmiennej funkcji.
2. **Koniec funkcji:** sprawdzane jest `.shares` bloku:
   - **0**: wpis zostaje czyszczony (shares, stan bloku), ale nie wraca na listę wolnych, tylko czeka na następne wywołanie,
   - **większe od 0**: blok „uciekł” (np. został zwrócony). Flaga `PERSISTENT` jest zdejmowana, blok staje się zwykłym blokiem nowego właściciela, a ukryta zmienna funkcji jest zerowana.
3. **Kolejne wywołanie:** jeśli ukryta zmienna wskazuje gotowy wpis, `.new` pomija rejestrację. Jeśli jest wyzerowana, przydzielany jest nowy wpis.
4. **Rekurencja:** jeśli wpis jest zajęty przez trwające wywołanie, kolejne wywołanie dostaje zwykły, nowy wpis.

---

## 8. Pliki mapowane

`.map` korzysta z mechanizmu systemu operacyjnego (w Linuksie `mmap`, w Windows `MapViewOfFile`):

- system rezerwuje w pamięci zakres adresów wielkości pliku, ale **niczego nie wczytuje**,
- przy pierwszym dostępie do danego miejsca procesor zgłasza systemowi brak strony, a system wczytuje z dysku tylko tę stronę (zwykle 4 KB),
- dawno nieużywane strony system sam usuwa z pamięci; zmienione strony zapisuje na dysk.

**Ochrona zapisu** (`MAPPED_WRITABLE`): plik otwarty bez `WRITABLE` jest podpinany ze stronami **tylko do odczytu**. Próbę zapisu zatrzymuje sam procesor, sprzętowo, więc w normalnej pracy ochrona nic nie kosztuje.

**Wpis w menedżerze:** adres to początek zmapowanego zakresu, długość to rozmiar pliku, flagi `MAPPED` i ewentualnie `MAPPED_WRITABLE`. Przy zwalnianiu menedżer zamiast zwykłego zwolnienia pamięci odpina plik (wcześniej wymuszając zapis zmian).

---

## 9. Optymalizacje kompilatora

Wszystkie optymalizacje dotyczą **maszynerii kompilatora**, nigdy operacji programisty: to, co programista napisał, zawsze się wykona.

### 9.1. Adres bloku odczytywany raz przed pętlą

Programista pisze:

```
for i = 0 to n-1 do
    ptr.float[i] = ptr.float[i] * 2
for.end
```

Kompilator generuje (zapis poglądowy):

```
adres = tablica[ptr].adres              # raz, przed pętlą
for i = 0 to n-1:
    pamięć_float[adres + i × 4] *= 2     # w środku: zwykły adres, prędkość C
```

Adres jest odczytywany ponownie tylko po operacjach, które mogą przenieść blok: `.update` i `.release` (także wywołanych w funkcji wołanej z pętli, jeśli kompilator nie może tego wykluczyć).

### 9.2. Usuwanie zbędnych zmian `.shares`

```
FUNCTION suma(dane as pointer): float
    ... tylko odczyt dane, bez przekazywania dalej ...
suma.end
```

Formalnie wejście do funkcji zwiększa `.shares` bloku o 1, a wyjście zmniejsza. Skoro funkcja tylko czyta blok i nigdzie go nie zapisuje ani nie przekazuje, a wywołujący i tak trzyma blok przez cały czas wywołania, para +1/−1 się znosi i kompilator jej nie generuje.

### 9.3. Sprawdzanie zakresu raz przed pętlą

```
for i = 0 to n-1 do
    x = ptr.float[i]
for.end
```

Kompilator sprawdza przed pętlą, czy `n × 4 ≤ ptr.length`:

- **tak**: wykonuje szybką wersję pętli, bez żadnych sprawdzeń w środku,
- **nie**: wykonuje wersję ze sprawdzaniem, która zachowuje się dokładnie według `.rangeError` i zasad odłamków.

Wynik programu jest w obu przypadkach identyczny, różni się tylko szybkość.

### 9.4. Operacje blokowe i SIMD

`ptr.float *= 2` jest zamieniane na pętlę przetwarzającą wiele elementów naraz (np. 8 floatów jedną instrukcją AVX):

```
pełne paczki po 8:   instrukcje wektorowe
reszta (0–7):        pojedynczo
odłamek na końcu:    ścieżka z rozdziału 6
```

---

## 10. Kompilacje cząstkowe i zależności

Kompilator dzieli program na cząstki (najczęściej pojedyncze funkcje) i przechowuje wyniki w `.bemol-cache/`. Dla każdej cząstki zapamiętuje:

- skrót (sumę kontrolną) jej kodu źródłowego,
- listę deklaracji, z których korzysta (`STRUCT`, `CONST`, `ALIAS`, `GLOBAL`, inne funkcje),
- skróty tych deklaracji w chwili kompilacji.

Przy kolejnej kompilacji cząstka jest kompilowana ponownie tylko wtedy, gdy zmienił się jej kod albo któraś z używanych deklaracji.

**Przykład:**

```
Color as STRUCT { R as unsigned_16, G as unsigned_16, B as unsigned_16, Alpha as unsigned_32 }

FUNCTION rozjasnij(...)     # używa Color
FUNCTION zapiszPlik(...)    # nie używa Color
```

Programista dodaje do `Color` pole. Rozmiar struktury zmienia się z 10 na 12 bajtów, a przesunięcia pól w `rozjasnij` są „wpieczone” w jej kod. Kompilator widzi, że skrót `Color` się zmienił:

- `rozjasnij` → kompilowana ponownie,
- `zapiszPlik` → zostaje bez zmian, z `.bemol-cache/`.

**`-finalbake`** wykorzystuje cząstki, ale optymalizuje cały program od nowa: wkleja małe funkcje w miejsca wywołań i usuwa niepotrzebny kod między funkcjami, czego przy osobnej kompilacji nie da się zrobić.
