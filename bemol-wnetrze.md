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
11. [Teksty w środku](#11-teksty-w-środku)
12. [`switch`: tablica skoków](#12-switch-tablica-skoków)

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
tekst (TEXT):  │ adres         │ pojemność     │shares │flg│wid│ dług. tekstu  │
widok (VIEW):  │ przesunięcie  │ długość       │shares │flg│ 0 │rodzic │ opis  │
               └───────────────┴───────────────┴───────┴───┴───┴───────┴───────┘
                 8 B             8 B             4 B    2 B 2 B  4 B     4 B
```

| Przesunięcie | Zwykły blok | Tekst (`TEXT`) | Widok (`VIEW`) |
|---|---|---|---|
| 0 (8 B) | adres bloku w pamięci | adres bloku | przesunięcie widoku w rodzicu |
| 8 (8 B) | długość w bajtach | pojemność w bajtach | długość widoku w bajtach |
| 16 (4 B) | `.shares` | `.shares` | `.shares` widoku |
| 20 (2 B) | flagi (16 bitów) | flagi | flagi |
| 22 (2 B) | liczba widoków | liczba widoków | 0 |
| 24 (4 B) | zarezerwowane | długość tekstu (8 B, razem z następnym polem) | numer rodzica |
| 28 (4 B) | zarezerwowane | | numer opisu prostokąta (0 = brak) |

O tym, jak czytać pola, decydują flagi `TEXT` (bit 5) i `VIEW` (bit 2). Obie korzystają z pola na przesunięciu 24, więc **wykluczają się nawzajem**: wpis jest albo tekstem, albo widokiem. Flagi, które tego pola nie używają (np. `MAPPED`), mogą łączyć się z każdym rodzajem.

### Flagi

```
bit:  15 14 13 12 11 10  9  8  7  6  5  4  3  2  1  0
      ─────────────────  ─────  ─  ─  ─  ─  ─  ─  ─  ─
           wolne        range PRD DBG TX MW MP VW PE GL
                        Error
```

| Bit | Skrót | Flaga |
|---|---|---|
| 0 | GL | `GLOBAL` |
| 1 | PE | `PERSISTENT` |
| 2 | VW | `VIEW` |
| 3 | MP | `MAPPED` |
| 4 | MW | `MAPPED_WRITABLE` |
| 5 | TX | `TEXT` |
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

**Pozycja w bajtach: `.at[n]`.** Przy `ptr.doublefloat.at[1009]` mnożenia nie ma: pozycja to po prostu bajt 1009, a soczewka wyznacza tylko szerokość (8 bajtów). Wartość może zaczynać się w dowolnym bajcie, a nowoczesne procesory x86 i ARM czytają ją jedną instrukcją, nawet gdy nie leży na granicy swojego rozmiaru.

**Szerokość zawsze z soczewki.** Odczyt `ptr.byte[n]` to zawsze 1 bajt, rozszerzony do 64-bitowego rejestru (instrukcja `movzx` na x86). Zapis do `ptr.byte[n]` to zawsze najmłodszy bajt rejestru. Kompilator nie musi patrzeć na drugą stronę przypisania, żeby ustalić, ile bajtów przeczytać.

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

**Wyjątek: pasek na widoku prostokątnym.** Pasek wycięty z prostokąta może obejmować kilka jego wierszy:

```
kafelek = blok.viewRectangle[2, 3, 4, 3, 10]     # bajty 32–35, 42–45, 52–55
pasek   = kafelek.viewPortion[2:4]               # bajty widoku 2, 3, 4, 5
```

Bajty 2–5 kafelka to w bloku 34, 35, 42, 43: dwa kawałki z dwóch różnych wierszy. Takiego układu nie da się zapisać jako jednego widoku paskowego ani prostokątnego na bloku. Dlatego rodzicem paska zostaje widok prostokątny, a adres bajtu nr k paska liczony jest w dwóch krokach:

```
1. bajt w kafelku = przesunięcie paska + k        (np. 2 + 0 = 2)
2. bajt w bloku   = adres jak dla kafelka (rozdział wyżej) dla bajtu 2 → 34
```

Prototyp tłumacza obsługuje ten przypadek właśnie tak.

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
for i as int = 0 to n-1 do
    ptr.float[i] = ptr.float[i] * 2
for.end
```

Kompilator generuje (zapis poglądowy):

```
adres = tablica[ptr].adres              # raz, przed pętlą
for i = 0 to n-1:
    pamięć_float[adres + i × 4] *= 2     # w środku: zwykły adres, prędkość C
```

Adres jest odczytywany ponownie tylko po operacjach, które mogą przenieść blok: `.new`, `.update`, `.release`, `.append` i podmianie bloku.

**Wywołania funkcji nie psują tej optymalizacji.** Według specyfikacji (sekcja 3, przekazywanie parametrów) funkcja może zmienić wpis bloku w menedżerze (rozmiar, adres, istnienie) tylko przez parametr `REF`. Po wywołaniu `rozjasnij(obraz)` kompilator wie, że `obraz` leży pod tym samym adresem i ma ten sam rozmiar, więc nie musi niczego odczytywać od nowa. Adres jest odświeżany tylko po wywołaniu z `REF` (`dopisz(REF obraz)`) i po wywołaniu funkcji oznaczonej jako „zmienia bloki globalne” (rozdział 9.5).

### 9.2. Usuwanie zbędnych zmian `.shares`

```
FUNCTION suma(dane as pointer): float
    ... tylko odczyt dane, bez przekazywania dalej ...
suma.end
```

Formalnie wejście do funkcji zwiększa `.shares` bloku o 1, a wyjście zmniejsza. Skoro funkcja tylko czyta blok i nigdzie go nie zapisuje ani nie przekazuje, a wywołujący i tak trzyma blok przez cały czas wywołania, para +1/−1 się znosi i kompilator jej nie generuje.

### 9.3. Sprawdzanie zakresu raz przed pętlą

```
for i as int = 0 to n-1 do
    x = ptr.float[i]
for.end
```

Kompilator sprawdza przed pętlą, czy `n × 4 ≤ ptr.size`:

- **tak**: wykonuje szybką wersję pętli, bez żadnych sprawdzeń w środku,
- **nie**: wykonuje wersję ze sprawdzaniem, która zachowuje się dokładnie według `.rangeError` i zasad odłamków.

Wynik programu jest w obu przypadkach identyczny, różni się tylko szybkość.

Sprawdzenie przed pętlą pozostaje ważne także wtedy, gdy w pętli wywoływane są funkcje bez `REF`: nie mogą one zmienić `ptr.size` (ta sama zasada co w 9.1).

### 9.4. Operacje blokowe i SIMD

`ptr.float *= 2` jest zamieniane na pętlę przetwarzającą wiele elementów naraz (np. 8 floatów jedną instrukcją AVX):

```
pełne paczki po 8:   instrukcje wektorowe
reszta (0–7):        pojedynczo
odłamek na końcu:    ścieżka z rozdziału 6
```

### 9.5. Granice ochrony `REF` i `CONST`: ta sama pamięć pod dwiema nazwami

`REF` i `CONST` chronią **nazwę**, a nie blok. Ten sam blok może być dostępny w funkcji pod inną nazwą (po angielsku *aliasing*), a wtedy ochrona parametru go nie obejmuje. Są dwie takie drogi:

**1. Zmienna `GLOBAL` wskazująca ten sam blok:**

```
GLOBAL bufor as pointer

FUNCTION przelicz(dane as pointer)        # bez REF: nie może zmienić rozmiaru „dane”
    bufor.update[1000000]                 # ...ale może przez GLOBAL, a to ten sam blok
przelicz.end

przelicz(bufor)
```

Kompilator rozwiązuje to tak:
- każda funkcja, która wykonuje `.new`, `.update`, `.release`, `.append` lub podmianę na zmiennej `GLOBAL` (sama albo przez funkcje, które wywołuje), dostaje cechę **„zmienia bloki globalne”**. Kompilator ustala ją sam, programista nic nie pisze,
- po wywołaniu takiej funkcji adresy bloków są odczytywane od nowa (9.1), a zakresy sprawdzane od nowa (9.3),
- przy kompilacjach cząstkowych (rozdział 10) cecha jest zapisana razem z opisem funkcji, więc działa także dla funkcji z innych plików i bibliotek.

**2. Ten sam blok przekazany do dwóch parametrów naraz:**

```
FUNCTION f(CONST zrodlo as pointer, REF cel as pointer)
...
f(obraz, REF obraz)        # zrodlo i cel to ten sam blok
```

Zapis do `cel` zmienia `zrodlo`, choć jest ono `CONST`, a `cel.release` zwalnia je w trakcie działania funkcji. Kompilator zgłasza **błąd**, gdy ta sama zmienna trafia do dwóch parametrów, z których choć jeden może zmieniać blok (bez znacznika lub `REF`). Dwa parametry `CONST` z tym samym blokiem są dozwolone, bo oba tylko czytają.

**Czego kompilator nie wykryje:** dwóch różnych zmiennych wskazujących ten sam blok (`a = b`, potem `f(a, REF b)`). To wymagałoby śledzenia każdego przypisania w całym programie. W kompilacji testowej menedżer łapie przynajmniej skutek: użycie zwolnionego bloku daje czytelny błąd zamiast cichych śmieci.

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

---

## 11. Teksty w środku

Tekst to zwykły blok z flagą `TEXT`. Różnica polega tylko na tym, jak menedżer czyta dwa pola wpisu:

```
t as text
t.new[16]
t = "abc"
```

| Pole wpisu | Wartość |
|---|---|
| adres | początek bloku |
| przesunięcie 8: pojemność | 16 |
| przesunięcie 24: długość tekstu | 3 |
| flagi | `TEXT` |

```
adres + 0  → 'a'
adres + 1  → 'b'
adres + 2  → 'c'
adres + 3  → koniec tekstu (długość tekstu = 3)
adres + 15 → ostatni bajt pojemności
```

Tekst zawsze zaczyna się od bajtu 0, więc przesunięcie końca tekstu jest równe jego długości. Odczyt `t.length` to jeden odczyt 8 bajtów z wpisu, bez szukania znaku końca jak w C.

**`t.append["def"]` krok po kroku:**

```
1. potrzeba = długość tekstu + 3 = 6
2. czy potrzeba ≤ pojemność (16)?  tak
3. skopiuj 3 bajty pod adres + 3
4. długość tekstu = 6
```

Gdy potrzeba przekracza pojemność, przed krokiem 3 wykonywane jest `.update[potrzeba]`: blok rośnie dokładnie do potrzebnego rozmiaru (może zostać przeniesiony, wtedy zmienia się adres we wpisie).

**Porównanie `a == b` dla tekstów:**

```
1. czy długość tekstu a == długość tekstu b?  nie → wynik 0 (natychmiast)
2. porównaj bajty (instrukcjami wektorowymi, po 16–32 bajty naraz)
```

Większość różnych tekstów różni się długością, więc zwykle porównanie kończy się w kroku 1.

---

## 12. `switch`: tablica skoków

Wartości w `case` są stałe, więc kompilator zna je podczas kompilacji i może zbudować **tablicę skoków**: dla każdej możliwej wartości adres gałęzi, która ma się wykonać.

```
switch kanal
    case 5                # gałąź A
    case 1 to 10          # gałąź B
    case @ANYTHING_ELSE   # gałąź C
switch.end
```

Kompilator przypisuje każdą wartość do **pierwszej pasującej gałęzi** (kolejność od góry):

| Wartość | Gałąź |
|---|---|
| 1, 2, 3, 4 | B |
| 5 | A (pierwsza pasująca) |
| 6, 7, 8, 9, 10 | B |
| pozostałe | C |

W działającym programie `switch` to wtedy:

```
1. czy kanal mieści się w zakresie tablicy (1–10)?  nie → gałąź C
2. skocz pod adres z tablicy[kanal - 1]
```

Jedno porównanie i jeden skok, niezależnie od liczby gałęzi. Gdy wartości są bardzo rozrzucone (np. `case 1` i `case 1000000`), kompilator zamiast ogromnej tablicy używa serii porównań albo wyszukiwania binarnego. Wynik jest zawsze ten sam, różni się tylko sposób wykonania.

Przy tym samym przypisywaniu kompilator wykrywa gałęzie martwe (żadna wartość nie trafia do gałęzi) i nakładanie się zakresów, i zgłasza odpowiednie ostrzeżenia.

**`@ANYTHING_ELSE` nic nie kosztuje.** Przy `case 1 to 10, @ANYTHING_ELSE` zamiast osobnej gałęzi C wiersz „pozostałe” w tabeli wskazuje po prostu gałąź B. Krok 1 w działającym programie brzmi wtedy: „czy kanal mieści się w zakresie tablicy? nie → gałąź B”. Ten sam kod co przy osobnej gałęzi `case @ANYTHING_ELSE`, tylko adres skoku jest inny.
