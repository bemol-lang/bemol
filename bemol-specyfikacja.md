# BEMOL ♭ — specyfikacja języka

> **BEMOL**: *Boundless Efficient Machine-Oriented Language*
> Repozytorium: `github.com/bemol-lang/bemol` · rozszerzenie plików: `.bmol`
> Jak język działa w środku: [**bemol-wnetrze.md**](bemol-wnetrze.md)
> Prototyp tłumacza BEMOL → C: folder [`prototyp/`](prototyp/README.md)
> Status: **szkic roboczy** · ostatnia aktualizacja: 2026-10-17

BEMOL to kompilowany język do szybkiego przetwarzania dużych bloków danych. Daje dostęp do pamięci z precyzją asemblera (każdy bajt, każdy bit), ale z czytelną składnią i automatycznym zarządzaniem pamięcią.

**Dlaczego „bemol”?** Bemol (♭) w muzyce obniża dźwięk. C# poszło „w górę”, ku wysokiemu poziomowi abstrakcji. BEMOL schodzi „w dół”, bliżej sprzętu, do bitów i bajtów.

---

## Spis treści

1. [Filozofia](#1-filozofia)
2. [Tryby kompilacji](#2-tryby-kompilacji)
3. [Składnia ogólna](#3-składnia-ogólna)
4. [Instrukcje sterujące](#4-instrukcje-sterujące)
5. [Typy, rozmiary i arytmetyka](#5-typy-rozmiary-i-arytmetyka)
6. [Literały](#6-literały)
7. [Typ `pointer`](#7-typ-pointer)
8. [Cykl życia bloku](#8-cykl-życia-bloku)
9. [Menedżer pamięci](#9-menedżer-pamięci)
10. [Soczewki: pozycja i szerokość](#10-soczewki-pozycja-i-szerokość)
11. [Odłamki: niepełne elementy](#11-odłamki-niepełne-elementy)
12. [Operacje blokowe](#12-operacje-blokowe)
13. [Operacje bitowe i inne operacje wbudowane](#13-operacje-bitowe-i-inne-operacje-wbudowane)
14. [Widoki i kopie fragmentów](#14-widoki-i-kopie-fragmentów)
15. [Pliki mapowane (`.map`)](#15-pliki-mapowane-map)
16. [Struktury (`STRUCT`)](#16-struktury-struct)
17. [Aliasy (`ALIAS`)](#17-aliasy-alias)
18. [Teksty (`text`)](#18-teksty-text)
19. [Wyjście poza blok: `.rangeError`](#19-wyjście-poza-blok-rangeerror)
20. [Ostrzeżenia i komunikaty błędów](#20-ostrzeżenia-i-komunikaty-błędów)
21. [Zestawienie operacji na `pointer`](#21-zestawienie-operacji-na-pointer)
22. [Kompilator](#22-kompilator)
23. [Narzędzia](#23-narzędzia)
24. [Język a biblioteka standardowa](#24-język-a-biblioteka-standardowa)
25. [Obiekty: klasy uproszczone](#25-obiekty-klasy-uproszczone)
26. [Zalecany styl](#26-zalecany-styl)
27. [Przykładowy program](#27-przykładowy-program)
28. [Otwarte pytania](#28-otwarte-pytania)

---

## 1. Filozofia

### Trzy cele BEMOL-a

Każda decyzja w języku jest sprawdzana względem trzech celów. Reguła, która psuje któryś z nich, wymaga ponownego przemyślenia.

1. **Jasność i przewidywalność kodu.** Wynik da się przewidzieć z samego zapisu, bez znajomości wyjątków i bez zaglądania w inne miejsca programu.
2. **Szybkie, proste i skuteczne zarządzanie pamięcią.** Blok jest zwalniany dokładnie w miejscu widocznym w kodzie (koniec zasięgu, ostatnie przypisanie, `.release`), bez *garbage collectora* i jego nieprzewidywalnych przerw w działaniu programu.
3. **Operacje na wielkich blokach danych.** Soczewki, widoki bez kopiowania, operacje na całym bloku zamieniane na instrukcje wektorowe procesora i pliki większe niż pamięć RAM.

### Zasady

**Wszystko jest blokiem pamięci.** Blok sam w sobie nie ma typu. Typ to **soczewka**, przez którą patrzymy na fragment bloku. Ten sam blok można w jednym programie czytać bajtami, liczbami, strukturami czy bitami.

**Każda operacja działa w ramach soczewki.** Przesunięcia bitów, operacje logiczne, arytmetyka, wypełnianie: zawsze dotyczą elementu, który wyznacza soczewka. `.byte` to każdy bajt osobno, `.value` to cały blok jako jedna liczba.

**Jedna notacja.** Wszystkie operacje na zmiennej zapisuje się po kropce: `nazwa.operacja`.

**Czytelnie dla człowieka, szybko dla maszyny.** Nazwy mówią wprost, co robią: wszystko, co kopiuje dane, zaczyna się od `copy`, a wszystko, co tylko pokazuje dane bez kopiowania, od `view`.

**Programista wie, co robi.** Programista BEMOL-a zna sposób zapisu danych w komputerze (wie, że 300 nie mieści się w bajcie) i ponosi za niego odpowiedzialność. Język nie zabrania mu dostępu do żadnego bajtu ani bitu; zabrania tylko zapisów niejednoznacznych, które łatwo przeczytać inaczej, niż działają (np. `=` w warunku).

**Kompilator wykonuje to, co programista napisał.** Kompilator optymalizuje tylko własną maszynerię (odczyt adresów, liczniki, kontrolę zakresu) i sposób wykonania (rejestry, instrukcje wektorowe, wyliczanie stałych), **nigdy nie pomija operacji programisty**. Jeśli programista napisał `.clear` tuż przed `.release`, blok zostanie wyzerowany.

**Co ma kosztować zero, musi być znane podczas kompilacji.** Rozmiary typów, stałe `CONST`, aliasy i struktury są ustalone przed uruchomieniem programu i kompilator po prostu je podstawia. Elastyczność dają zmienne, indeksy i widoki.

**Nic kosztownego nie dzieje się bez wiedzy programisty.** Kontrole i pomoce (wzory pamięci, ostrzeżenia, `HALT`) programista włącza świadomie, a w finalnym programie może je wyłączyć tam, gdzie liczy się każdy cykl.

**Błąd mówi co, gdzie, dlaczego i jak naprawić.** Komunikaty kompilatora i programu są przejrzyste dla człowieka i jednoznaczne dla agenta AI (sekcja 20).

**Proste dla człowieka na zewnątrz, optymalne dla maszyny w środku.** Programista opisuje, czego chce, a rachunek przesunięć i adresów wykonują kompilator i menedżer pamięci. Jak to działa w środku, opisuje osobny dokument [**bemol-wnetrze.md**](bemol-wnetrze.md): im lepiej programista rozumie wnętrze języka, tym lepiej rozumie narzędzie, którym pracuje.

**Kolejność bajtów: little-endian.** Bajt 0 jest najmniej znaczący. Blok czytamy jak zapis binarny, „od prawej do lewej”. To naturalny porządek procesorów x86 i ARM.

**Indeksowanie od zera.**

**Każda nietypowa decyzja ma uzasadnienie.** Tam, gdzie BEMOL robi coś inaczej niż popularne języki, specyfikacja zawiera ramkę **„Dlaczego tak?”**: programista dostaje nie tylko regułę, ale i powód, często wynikający z błędów, które latami utrudniały życie w C, C++ czy Javie.

---

## 2. Tryby kompilacji

| Tryb | Do czego | Jak uruchomić |
|---|---|---|
| **kompilacja testowa** | szybkie kompilacje cząstkowe do uruchamiania i testowania programu | `bemol program.bmol` (domyślnie) |
| **finalbake** | „wypieczenie” wszystkich cząstek w jedno spójne, w pełni zoptymalizowane dzieło | `bemol -finalbake program.bmol` |

W środowisku programistycznym te same tryby wybiera się z menu.

**W kodzie programu nie zapisuje się trybu kompilacji.** Ten sam kod źródłowy daje obie wersje bez żadnej edycji.

Programista może jedynie **sprawdzić** tryb przez wbudowaną stałą tylko do odczytu:

```
if BUILD_MODE == TEST then
    wypiszStanPamieci()
if.end
```

`BUILD_MODE` ma wartość `TEST` lub `FINALBAKE` i jest znana podczas kompilacji. Kod w gałęzi, która w danym trybie nigdy się nie wykona, nie jest dołączany do programu (to nie łamie zasady z sekcji 1: programista sam napisał warunek, który mówi, kiedy kod ma działać).

---

## 3. Składnia ogólna

### Wielkość liter

Język rozróżnia wielkość liter.

- **Słowa kluczowe budujące strukturę programu lub decydujące o życiu zmiennych piszemy WIELKIMI literami** (wymagane): `MAIN`, `BEGIN`, `END`, `CLASS`, `FUNCTION`, `STRUCT`, `ENUM`, `GLOBAL`, `PERSISTENT`, `CONST`, `REF`, `ALIAS`, `PRIVATE`.
- **Słowa przepływu sterowania, operatory, funkcje wbudowane i łączniki piszemy małymi literami:** `if`, `then`, `elseif`, `else`, `for`, `to`, `step`, `do`, `while`, `repeat`, `until`, `foreach`, `in`, `break`, `continue`, `switch`, `case`, `as`, `return`, `this`, `and`, `or`, `xor`, `not`, `shl`, `shr`, `rol`, `ror`, `saturate`, `print`, `println`.
- **Wbudowane stałe programu** piszemy wielkimi literami: `BUILD_MODE`, `ARGS`.
- **Wieloczłonowe nazwy wbudowane w język** piszemy z wielką literą na początku kolejnych słów: `rangeError`, `copyPortion`, `viewRectangle`.
- **Znaczniki** zaczynają się od `@`: `@ACCEPT` (potwierdzenie ostrzeżenia, sekcja 20) i `@ANYTHING_ELSE` (gałąź „wszystko inne” w `case`, sekcja 4). Znak `@` jest zarezerwowany dla nich i znaczy zawsze to samo: **to nie jest wartość ani nazwa, tylko znacznik dla kompilatora**. Dzięki temu znacznika nie da się pomylić ze stałą `CONST` ani wartością `ENUM`, które też pisze się wielkimi literami.
- **Nazwy zmiennych, funkcji, klas, stałych i wartości wyliczeń programisty są dowolne.** Zalecenia stylu: sekcja 26.

### Komentarze

Komentarz zaczyna się od `#` i trwa do końca linii:

```
licznik = 0          # zerowanie licznika
```

### Separatory instrukcji

**Instrukcję kończy koniec linii albo `;`.** Średnik pozwala zapisać kilka instrukcji w jednej linii:

```
a = 1; b = 2; c = 3
if x > 5 then y = 1; if.end
```

- `;` na końcu linii jest dozwolone, ale zbędne. Kto przyjdzie z C i odruchowo je postawi, nie dostanie błędu,
- pusty `;` (np. `;;`) nie jest błędem, ale środowisko podpowiada, że jest zbędny,
- **długie wyrażenie można przenieść do następnej linii**, gdy linia kończy się operatorem, przecinkiem lub otwartym nawiasem:

```
wynik = pierwsza_wartosc + druga_wartosc +
        trzecia_wartosc
kafelek = obraz.viewRectangle[100*Color, 50,
                              64*Color, 64, SZER*Color]
```

### Zamykanie bloków

Każdy blok zamyka się swoją nazwą z przyrostkiem `.end`:

```
for i as int = 1 to 10 do
    ...
for.end

if warunek then
    ...
if.end

FUNCTION potega(...): float
    ...
potega.end

CLASS Calculate
    ...
Calculate.end
```

**Wyjątki:**

- program główny ma wyróżnione granice `MAIN BEGIN` / `MAIN END`, żeby od razu rzucały się w oczy,
- pętlę `repeat` zamyka linia `until warunek` (sekcja 4), bo czyta się jak zdanie.

### Układ pliku

`GLOBAL`, `CONST`, `STRUCT`, `ENUM`, `ALIAS`, `CLASS` i `FUNCTION` mogą stać **w dowolnym miejscu pliku, poza MAIN i poza funkcjami**. Kompilator najpierw zbiera wszystkie deklaracje z całego pliku, więc kolejność nie ma znaczenia. Funkcje mogą stać pod programem głównym.

Zalecany styl (niewymagany):

```
GLOBAL ...
CONST ...
STRUCT ...

MAIN BEGIN
    ...
MAIN END

FUNCTION ...
CLASS ...
```

### Deklaracje

```
licznik as int
temp as float = 1                  # inicjalizacja przy deklaracji
GLOBAL ptr as pointer              # zmienna globalna
CONST ROZMIAR as int = 1024        # stała
```

**Zmienne `GLOBAL`** deklaruje się poza funkcjami i MAIN. Są widoczne w całym programie i gotowe przed startem MAIN, niezależnie od miejsca w pliku.

**Stałe `CONST`** mają zawsze jawny typ. Są wyliczane podczas kompilacji i wbudowywane w kod jako gotowe wartości. Muszą być jednoznaczne: zależność od wartości znanej dopiero w czasie działania albo zapętlona zależność (`A` zależy od `B`, a `B` od `A`) to błąd kompilacji. Kompilator sam ustala kolejność wyliczania stałych zależnych od siebie.

### Zasięg zmiennych

**1. Zmienna żyje od deklaracji do końca bloku, w którym ją zadeklarowano.** Blokiem jest funkcja, `MAIN`, każde `if`, `for`, `while`, `foreach`, `repeat` i gałąź `case`:

```
for i as int = 0 to 100 do
    x as doublefloat = i * 0.01
    ...
for.end
# tu ani i, ani x już nie istnieją
```

**2. W funkcji zmienną trzeba zadeklarować przed użyciem.** Swoboda kolejności dotyczy tylko deklaracji na poziomie pliku. Wewnątrz funkcji kod czyta się z góry na dół.

**3. Bez przesłaniania nazw.** Zmienna wewnętrzna nie może mieć tej samej nazwy co zmienna z bloku zewnętrznego, parametr funkcji czy zmienna `GLOBAL`. To błąd kompilacji.

> **Dlaczego bez przesłaniania?** W C i C++ zmienna wewnętrzna może mieć tę samą nazwę co zewnętrzna i ją „przykryć”. Programista zmienia wtedy inną zmienną, niż myśli. W BEMOL-u jedna nazwa w danym miejscu oznacza zawsze jedną rzecz.

**4. Koniec bloku to koniec życia bloku pamięci.** Zmienna `pointer` zadeklarowana w bloku kodu zmniejsza `.shares` przy jego `.end`. Jeśli nikt inny jej nie trzyma (i nie ma widoków), pamięć jest zwalniana dokładnie w tym miejscu, widocznym w kodzie.

**5. Zmienne zadeklarowane w pętli powstają w każdym obrocie od nowa.** Dla liczb nic to nie kosztuje. `.new` wewnątrz pętli oznacza jednak przydział pamięci w każdym obrocie, więc kompilator zgłasza informację z podpowiedzią: przenieś deklarację przed pętlę albo użyj `PERSISTENT`.

### Funkcje

```
FUNCTION potega(base as float, times as int): float
    temp as float = 1
    for i as int = 1 to times do
        temp = temp * base
    for.end
    return temp
potega.end
```

Wartość zwraca się zwykłym `return`. Metody klasy zapisuje się z kropką na początku nazwy (`FUNCTION .multiply(...)`).

### Przekazywanie parametrów

**1. Zmienne statyczne (`int`, `float`, `STRUCT`...) są kopiowane.** Funkcja nie może przypadkiem zmienić zmiennej wywołującego. Kopiowanie liczb jest praktycznie darmowe, bo trafiają do rejestrów procesora.

```
FUNCTION podwoj(x as int): int
    x = x * 2          # zmienia tylko lokalną kopię
    return x
podwoj.end
```

**2. Bloki (`pointer`, `text`) są przekazywane wskaźnikiem.** Kopiowany jest tylko 4-bajtowy numer bloku, nigdy dane. Funkcja pracuje na tym samym bloku co wywołujący, więc zmiany danych są widoczne na zewnątrz.

```
FUNCTION rozjasnij(obraz as pointer)
    obraz.byte = saturate(obraz.byte + 20)    # zmienia dane wywołującego
rozjasnij.end
```

**Trzy poziomy uprawnień funkcji do bloku**, każdy z własnym znacznikiem w deklaracji. Zasada: **dane bloku zmienia każda funkcja bez `CONST`; wpis bloku w menedżerze (rozmiar, adres, istnienie) zmienia tylko funkcja z `REF`.**

| Deklaracja | Dane bloku | `.new`, `.update`, `.release`, `.append`, podmiana `=` |
|---|---|---|
| `CONST dane as pointer` | tylko odczyt | ✘ |
| `dane as pointer` | odczyt i zapis | ✘ |
| `REF dane as pointer` | odczyt i zapis | ✔ |

- **bez znacznika** funkcja pracuje na danych bloku wszystkimi narzędziami, które nie zmieniają jego wpisu w menedżerze (zapis, operacje blokowe, `.fill`, `.clear`, widoki). Operacje zmieniające rozmiar, adres lub istnienie bloku to błąd kompilacji z podpowiedzią „dodaj `REF`”,
- **`CONST`** to deklaracja intencji: blok jest w tej funkcji tylko dawcą danych. Każda próba zapisu to błąd kompilacji. Wywołujący ma gwarancję, że funkcja nie zmieni jego danych, a kompilator może śmielej optymalizować,
- **`REF`** świadomie dopuszcza zmianę wpisu w menedżerze, ze wszystkimi skutkami: przy podmianie stary blok dostaje `.shares - 1` (i jest zwalniany, gdy licznik spadnie do 0, a nie patrzą na niego widoki), nowy `.shares + 1`. Sam `REF` liczników nie zmienia: parametr `REF` to inna nazwa tej samej zmiennej wywołującego, a nie druga zmienna.

**`CONST` obowiązuje do końca funkcji, także w funkcjach, które ona wywołuje:**

- blok `CONST` przekazany dalej może trafić tylko do parametru `CONST`. Przekazanie go do parametru bez znacznika albo z `REF` to błąd kompilacji,
- widok utworzony z bloku `CONST` też jest `CONST`,
- kopia (`dane.copy`, `copyPortion`, `copyRectangle`) to nowy blok, więc wolno ją zmieniać.

**Ten sam blok w dwóch parametrach naraz** (`f(obraz, REF obraz)`) to błąd kompilacji, gdy choć jeden z tych parametrów może zmieniać blok (bez znacznika lub z `REF`). Inaczej zapis przez jeden parametr zmieniałby drugi, nawet oznaczony `CONST`, a `.release` zwalniałoby go w trakcie działania funkcji. Dwa parametry `CONST` z tym samym blokiem są dozwolone. Ochrona `REF` i `CONST` dotyczy nazwy parametru, a nie bloku: o drodze przez zmienne `GLOBAL` i o tym, czego kompilator nie wykryje, mówi [bemol-wnetrze.md, rozdział 9.5](bemol-wnetrze.md#95-granice-ochrony-ref-i-const-ta-sama-pamięć-pod-dwiema-nazwami).

```
FUNCTION suma(CONST dane as pointer): longint     # tylko czyta
FUNCTION rozjasnij(obraz as pointer)              # zmienia dane, rozmiar zostaje
FUNCTION dopisz(REF lista as pointer)             # może zmienić rozmiar
FUNCTION zwolnij(REF b as pointer)                # może zwolnić lub podmienić blok
    b.release
zwolnij.end

zwolnij(REF obraz)
```

> **Dlaczego zmiana rozmiaru wymaga `REF`?** Po wywołaniu funkcji bez `REF` wszystko, co wywołujący wiedział o bloku, pozostaje prawdą: `blok.size` sprzed wywołania jest aktualne, a blok leży pod tym samym adresem. Programista nie dostaje niespodzianek, a kompilator może liczyć adres bloku raz przed pętlą, nawet gdy w pętli wywoływane są funkcje. Każdą zmianę rozmiaru, podmianę czy zwolnienie widać w miejscu wywołania: `dopisz(REF lista)`.

**3. `REF`: gdy funkcja ma zmienić zmienną wywołującego**, czyli wartość zmiennej statycznej albo wpis bloku w menedżerze (rozmiar, podmiana, zwolnienie). `REF` jest wymagane **także w miejscu wywołania**:

```
FUNCTION zamien(REF a as int, REF b as int)
    t as int = a; a = b; b = t
zamien.end

zamien(REF x, REF y)
```

> **Dlaczego `REF` także przy wywołaniu?** W C++ zapis `f(x)` nie mówi, czy zmienna `x` się zmieni: trzeba zajrzeć do deklaracji funkcji. W BEMOL-u w miejscu wywołania widać każdą zmianę samej zmiennej: nowej wartości liczby albo rozmiaru, podmiany lub zwolnienia bloku. Zmiana *danych* bloku nie wymaga `REF`, bo to zwykła praca funkcji na bloku; o tym, że funkcja danych nie zmieni, informuje `CONST` w jej deklaracji.

**4. Funkcja bez wyniku** nie ma nic po nawiasie (żadnego `: typ`). `return wartość` w takiej funkcji to błąd kompilacji, samo `return` (wcześniejsze wyjście) jest dozwolone.

**5. Kilka wartości zwracanych naraz:**

```
FUNCTION minmax(CONST dane as pointer): int, int
    ...
    return najmniejsza, najwieksza
minmax.end

mn, mx = minmax(pomiary)
```

To czytelniejsze niż zwracanie wyników przez `REF`. `REF` zostaje dla przypadków, gdy funkcja zmienia istniejącą wartość, a nie produkuje nową.

### Wypisywanie: `print` i `println`

```
print("Rozmiar obrazu: ", obraz.size)          # bez przejścia do nowej linii
println("Rozmiar obrazu: ", obraz.size)        # z przejściem do nowej linii
```

- dowolna liczba argumentów po przecinku, różnych typów: teksty, liczby, `bit`, wartości `ENUM` (wypisywane nazwą),
- wynik trafia na standardowe wyjście programu (konsola).

**Format liczb** po dwukropku:

```
println(kolor : hex)        # &FF00h
println(flagi : bin)        # &0110b
println(pi : 3)             # 3.142 (3 miejsca po przecinku)
```

Liczby szesnastkowe i binarne są wypisywane **w tym samym zapisie co literały w kodzie** (`&...h`, `&...b`), więc wynik można wkleić z powrotem do programu. Najbardziej znaczące cyfry stoją po lewej.

**Zrzut bloku:** blok lub widok wypisany z `: hex` pokazuje bajty **w kolejności adresów**, po 16 w linii, z przesunięciem na początku linii. Widok prostokątny wypisywany jest wiersz po wierszu, więc od razu widać, co „wycina”:

```
println(obraz.viewPortion[0:32] : hex)
```

```
000000: 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F
000010: 10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 1E 1F
```

**Blok bez formatu** wypisuje krótki opis zamiast zawartości, żeby przypadkiem nie wypisać gigabajtów danych:

```
println(obraz)              # blok #17, 20 736 000 B, shares 1, widoki 0
```

**Zmienna liczba argumentów tylko dla funkcji wbudowanych.** `print` i `println` są wbudowane w kompilator: podczas kompilacji rozkłada on wywołanie na serię prostych wywołań, bo zna typ każdego argumentu. Funkcje programisty mają stałą liczbę parametrów; gdy trzeba przekazać „dowolnie wiele” wartości, przekazuje się blok.

> **Dlaczego nie ma `...` jak w C?** W C funkcja ze zmienną liczbą parametrów (`int printf(const char *format, ...)`) traci informację o ich typach i sama musi zgadywać, co dostała. `printf("%d", 3.14)` wypisuje śmieci, a takie pomyłki bywały nawet dziurami bezpieczeństwa. W BEMOL-u typy argumentów `print` zna kompilator.

### Czytanie z klawiatury: `keyInput`

Prosty odczyt linii wpisanej przez człowieka, jak `readln` w Pascalu albo `scanf` w C, ale bez ich pułapek:

```
imie as text
wiek as byte
keyInput("Jak masz na imię? ", REF imie)
keyInput("Ile masz lat? ", REF wiek)
keyInput("Szerokość: ", REF szer, "Wysokość: ", REF wys)     # kilka pytań w jednym wywołaniu
keyInput()                                                 # czeka na Enter
keyInput("Naciśnij Enter...")                              # tekst i czekanie na Enter
```

- **teksty w cudzysłowie** są wypisywane jako pytanie, **`REF zmienna`** dostaje odpowiedź. `REF` stoi przy wywołaniu tak jak przy każdej funkcji, która zmienia zmienną (sekcja 3, parametry),
- **jedna linia na jedną zmienną**, zakończona Enterem; znak końca linii (także `\r` z Windows) nie trafia do zmiennej,
- **stały bufor 255 bajtów.** Dłuższa linia jest odrzucana w całości z prośbą o ponowne wpisanie, więc nie ma przepełnienia bufora ani „resztek” czytanych przez następne pytanie,
- **liczby są sprawdzane według typu zmiennej**: zły zapis (`abc`) albo wartość spoza zakresu (`300` dla `byte`) daje komunikat i ponowienie tego samego pytania. Program nie dostaje nigdy połowicznie wczytanej ani przekręconej liczby. Dla `float` i `doublefloat` przyjmowana jest kropka i przecinek (`3.5`, `3,5`), spacje na początku i końcu są pomijane,
- **tekst dostaje dokładnie tyle bajtów, ile wpisano**: `keyInput` robi `.new` albo `.update` na długość odpowiedzi i zapisuje ją w polu długości tekstu w menedżerze (sekcja 18). Bez zera na końcu, bo długość jest znana,
- **koniec danych wejściowych** w czasie czekania na odpowiedź (np. wejście z pliku się skończyło) to błąd `BML-E0130`.

```
Ile masz lat? abc
[ ! ] To nie jest liczba typu byte (0...255), wpisz jeszcze raz
Ile masz lat? 300
[ ! ] To nie jest liczba typu byte (0...255), wpisz jeszcze raz
Ile masz lat? 42
```

### Czytanie danych wejściowych: `INPUT.read`

Do dużych danych (plik przekierowany na wejście programu, dane z innego programu) służy odczyt porcjami do bloku:

```
bufor as pointer
bufor.new[65536]                     # wielkość porcji wybiera programista
n as longint = INPUT.read[bufor]
while n > 0 do
    ...                              # w buforze jest n nowych bajtów
    n = INPUT.read[bufor]
while.end
```

- **`INPUT.read[bufor]` wypełnia blok kolejnymi bajtami wejścia** i zwraca ich liczbę. Wynik może być mniejszy niż `bufor.size` (ostatnia porcja); **0 oznacza koniec danych**,
- **bajty są czytane bez zmian**: bez zamiany końców linii, bez interpretacji kodowania. Dla bloku `text` wynik trafia też do pola długości tekstu,
- **rozmiar bloku się nie zmienia.** To programista decyduje, ile pamięci zajmuje porcja, a pętla odczytu nie przydziela pamięci w kółko,
- działa także z widokiem jako buforem (np. czytanie wprost do fragmentu większego bloku).

> **Dlaczego dwa sposoby czytania?** Człowiek przy klawiaturze wpisuje krótkie linie i myli się, więc `keyInput` pilnuje typu, zakresu i długości. Dane z pliku mogą mieć gigabajty i dowolną zawartość, więc `INPUT.read` czyta surowe bajty dużymi porcjami do bloku, na którym działają wszystkie soczewki. Jedna funkcja „do wszystkiego” byłaby albo niewygodna dla człowieka, albo za wolna dla danych.

### Start i koniec programu

```
MAIN BEGIN
    if ARGS.count < 2 then
        println("Użycie: program plik.raw")
        return 1                     # kod zakończenia: błąd
    if.end
    nazwa as text = ARGS[1]          # argumenty jako teksty, ARGS[0] to nazwa programu
    ...
    return 0                         # kod zakończenia: sukces
MAIN END
```

- **argumenty z linii poleceń** są w wbudowanej stałej `ARGS`: `ARGS.count` to ich liczba, `ARGS[n]` to n-ty argument jako `text`,
- **`return` w `MAIN`** kończy program i zwraca kod zakończenia do systemu (0 = sukces, inne = błąd). Dojście do `MAIN END` bez `return` oznacza 0.

### Stos i sterta

- **Zmienne statyczne, o stałym rozmiarze** (`int`, `float`, `byte`...), trafiają na **stos**. Procesor przydziela i zwalnia dla nich miejsce jedną instrukcją przy wejściu do funkcji i wyjściu z niej, więc kosztują praktycznie zero. Każde wywołanie funkcji, także rekurencyjne, ma własne kopie.
- **Zmienne `pointer`** mają blok na **stercie** i wpis w menedżerze pamięci (sekcja 9).

---

## 4. Instrukcje sterujące

### Porównania

| Operator | Znaczenie |
|---|---|
| `==` | równe |
| `!=` | różne |
| `<` `>` | mniejsze / większe |
| `<=` `>=` | mniejsze lub równe / większe lub równe |

**`=` zawsze oznacza przypisanie, `==` zawsze porównanie.** Przypisanie jest osobną instrukcją i nie może stać wewnątrz wyrażenia, więc `if x = 5 then` jest błędem kompilacji z podpowiedzią „czy chodziło o `==`?”.

> **Dlaczego przypisanie nie może stać w warunku?** W C zapis `if (x = 5)` jest poprawny: przypisuje 5 i zawsze jest prawdziwy. To jeden z najsłynniejszych błędów w historii programowania. W BEMOL-u nie da się go popełnić.

**Wynik porównania ma typ `bit`** (0 lub 1). Porównywane wartości są liczone na 64 bitach (sekcja 5, zasada Z1), więc np. `if a + b > 255 then` działa także dla bajtów.

### Operatory logiczne

`and`, `or`, `not` to te same słowa co dla operacji bitowych (sekcja 13). Na wartościach typu `bit`, czyli wynikach porównań, działają po prostu jak operatory logiczne.

- **Warunek w `if`, `while`, `until` itd. musi mieć typ `bit`.** Zapis `if licznik then` przy `licznik as int` jest błędem, trzeba napisać `if licznik != 0 then`. Zero zgadywania, co autor miał na myśli.
- **Skracanie obliczeń:** w `if a > 0 and ptr.byte[a] == 5 then` drugi warunek nie jest sprawdzany, gdy pierwszy jest fałszywy (analogicznie dla `or`, gdy pierwszy jest prawdziwy). To chroni np. przed odczytem spod złego indeksu.

### Warunki: `if`

```
if temperatura > 30 then
    stan = GORACO
elseif temperatura > 15 then
    stan = CIEPLO
else
    stan = ZIMNO
if.end
```

- `elseif` to jedno słowo, więc cały łańcuch zamyka jedno `if.end`,
- `then` jest obowiązkowe,
- **`if.end` zawsze, także dla jednej linii**: `if x > 5 then y = 1; if.end`.

> **Dlaczego zawsze `if.end`?** W C brak wyraźnego zamknięcia prowadzi do pomyłek, do którego `if` należy `else`, i do błędów, gdy ktoś dopisze drugą linię do „jednolinijkowego” warunku. Jedna forma, zero wątpliwości.

### Pętla `for`: licznik od–do

```
for i as int = 0 to 9 do ... for.end                  # 0, 1, ..., 9 (koniec włącznie)
for i as int = 0 to 100 step 5 do ... for.end         # 0, 5, 10, ..., 100
for i as int = 10 to 0 step -1 do ... for.end         # w dół
```

- bez `step` krok wynosi 1; gdy początek jest większy od końca, pętla wykonuje się zero razy (liczenie w dół wymaga jawnego `step -1`),
- **początek, koniec i krok muszą być liczbami całkowitymi** (ramka niżej).

**Typ licznika jest zawsze jawny.** Są dwie dozwolone formy:

| Zapis | Znaczenie |
|---|---|
| `for i as int = 0 to 10` | nowy licznik zadeklarowanego typu całkowitego, istnieje **tylko w pętli** |
| `for i = 0 to 10`, gdy `i` zadeklarowano wcześniej | używa istniejącej zmiennej całkowitej; **po pętli zostaje w niej ostatnia wartość, jaką wpisała pętla** (jeśli pętla nie wykonała się ani razu, zmienna jest nietknięta) |
| `for i = 0 to 10` bez deklaracji `i` | **błąd kompilacji** z podpowiedzią obu powyższych form |

Licznik zadeklarowany w pętli znika po `for.end`, a użycie go dalej jest błędem z czytelną podpowiedzią:

```
*****************************************************************
ERROR: BML-E0300
petla.bmol
at line 11, column 32
-----------------------------------------------------------------
11 |     println("ostatnie i = ", i)
   |                              ^
-----------------------------------------------------------------
  [ ! ] Nieznana nazwa „i”
  [ i ] „i” istniało tylko w pętli for z linii 8 i zniknęło po for.end
[ tip ] jeśli wartość jest potrzebna po pętli, zadeklaruj „i as int” przed pętlą i pisz: for i = ...
_________________________________________________________________
```

Licznik zadeklarowany wcześniej przydaje się np. do znalezienia miejsca, w którym pętlę przerwało `break`:

```
i as int
for i = 0 to 999 do
    if dane.byte[i] == 0 then break; if.end
for.end
println("pierwsze zero na pozycji ", i)
```

**Zapis licznika przez soczewkę:** `blok.byte[i] = i` zapisuje zawsze 1 bajt, czyli najmłodszy bajt licznika, bez względu na typ `i`. Soczewka pisze swoją szerokość (sekcja 10, zasada Z3).

**Ochrona przed pętlą bez końca.** Pętla `for j as byte = 0 to 255` w języku z zawijaniem liczb (jak C) nigdy by się nie skończyła: po 255 licznik wraca do 0, więc warunek „j ≤ 255” jest zawsze prawdziwy. W BEMOL-u kompilator liczy obroty wewnętrznie w szerokim liczniku, a zmienna `j` dostaje w każdym obrocie jego wartość. Pętla zawsze się kończy. Gdy początek lub koniec nie mieści się w typie licznika (`for j as byte = 0 to 300`), to błąd kompilacji, a przy wartościach znanych dopiero w działaniu programu jedno sprawdzenie przed startem pętli.

Wartość ułamkową liczy się w środku pętli z licznika:

```
for i as int = 0 to 100 do
    x as doublefloat = i * 0.01      # 0, 0.01, ..., 1
    ...
for.end
```

> **Dlaczego `for` przyjmuje tylko liczby całkowite?**
> Liczby takie jak 0.01 nie dają się zapisać w systemie dwójkowym dokładnie, tak jak 1/3 w dziesiętnym. Gdy pętla co obrót dodaje ułamkowy krok, błędy się sumują: po stu krokach 0.01 wychodzi 0.99999999999999 albo 1.00000000000001. W językach, które na to pozwalają (C, C++, Java, JavaScript), pętla „od 0 do 1 co 0.01” wykonuje się raz 100, a raz 101 razy, zależnie od kierunku błędu. To jeden z trudniejszych do znalezienia błędów.
> W BEMOL-u licznik pętli jest zawsze liczbą całkowitą, więc liczba obrotów jest dokładna i widoczna w kodzie. Wartość ułamkowa liczona z licznika (`x = i * 0.01`) jest wyliczana za każdym razem od nowa, więc błąd się nie kumuluje.

Zapis `for x as doublefloat = 0 to 1 step 0.01` to błąd kompilacji z podpowiedzią, jak go przepisać.

> **Dlaczego typ licznika musi być jawny?** Licznik to zwykła zmienna, a w BEMOL-u każda zmienna ma jawny typ. Typ w nagłówku pętli mówi od razu, jaki zakres licznik obejmie (kompilator sprawdza go przed startem pętli), a deklaracja w pętli lub przed nią mówi, czy licznik przetrwa `for.end`.

### Pętla `while`: warunek na początku

```
while pozycja < koniec do
    ...
while.end
```

### Pętla `repeat ... until`: warunek na końcu

Wnętrze wykona się co najmniej raz. Linia `until warunek` zamyka blok:

```
repeat
    odczytajPakiet()
until koniecDanych
```

### Pętla `foreach`: po każdym elemencie soczewki

Najważniejsza pętla BEMOL-a:

```
foreach px in obraz.Color do
    px.R = 255 - px.R
foreach.end

foreach px, i as int in kafelek.Color do      # z numerem elementu
    ...
foreach.end
```

- **numer elementu ma jawny typ całkowity**, tak jak licznik pętli `for`,
- **`px` nie jest kopią, tylko nazwą elementu w bloku**, jak alias. Zapis do `px.R` zmienia dane w bloku,
- działa na blokach, widokach paskowych i prostokątnych (przy prostokącie kompilator sam przechodzi wiersz po wierszu),
- kompilator wie, że iteracje dotyczą kolejnych elementów, więc łatwo zamienia pętlę na instrukcje wektorowe.

### Przerywanie pętli

- `break` wychodzi z pętli,
- `continue` przechodzi do następnego obrotu.

Oba działają na najbliższą pętlę. Wyjście z kilku zagnieżdżonych pętli naraz: do ustalenia (sekcja 28).

### Wybór: `switch` / `case`

```
switch kanal
    case 0
        nazwa = CZERWONY
    case 1, 2
        nazwa = ZIELONY_LUB_NIEBIESKI
    case 10 to 20
        nazwa = ZAKRES
    case @ANYTHING_ELSE
        nazwa = NIEZNANY
switch.end
```

- **bez „przelatywania”**: każdy `case` kończy się sam, gdy zaczyna się kolejny, więc nie ma `break`. Kilka wartości po przecinku, zakres przez `to`,
- **wartości w `case` muszą być stałe** (literały albo `CONST`). Kompilator zamienia `switch` na tablicę skoków, czyli jeden skok zamiast serii porównań,
- **tylko liczby całkowite, `bit` i wartości `ENUM`**, bez floatów (porównanie na równość liczb zmiennoprzecinkowych jest zawodne),
- **w `switch` nie ma `else`.** Wartości, których nie złapał żaden `case`, obsługuje gałąź ze znacznikiem `@ANYTHING_ELSE` (niżej),
- **gałąź „wszystko inne” jest opcjonalna**: gdy nic nie pasuje i nie ma `@ANYTHING_ELSE`, żadna gałąź się nie wykonuje, a program przechodzi do instrukcji po `switch.end`.

**`@ANYTHING_ELSE`: „wszystko inne”.** Znacznik może stać sam (`case @ANYTHING_ELSE`, jak w przykładzie wyżej) albo na liście wartości istniejącego `case`. To drugie przydaje się, gdy wszystko inne ma być obsłużone tak samo jak konkretne wartości:

```
switch kanal
    case 0
        nazwa = CZERWONY
    case 1, 2
        nazwa = ZIELONY_LUB_NIEBIESKI
    case 10 to 20, @ANYTHING_ELSE
        nazwa = ZAKRES                  # 10...20 oraz każda wartość, której nie złapał inny case
    case 30
        nazwa = SPECJALNY
switch.end
```

- **bez kopiowania kodu i bez przestawiania gałęzi**: wiadomo od razu, która gałąź przejmuje wszystko inne,
- **`@ANYTHING_ELSE` może być w `switch` tylko raz.** Drugi to błąd kompilacji, bo dwie gałęzie miałyby ten sam warunek,
- **może stać przy dowolnym `case`, nie tylko ostatnim.** Łapie tylko wartości, których nie obsługuje żaden inny `case`, więc kolejność od góry go nie dotyczy (`case 30` w przykładzie działa normalnie),
- przy `ENUM` wyłącza ostrzeżenie o brakujących wartościach.

> **Dlaczego w `switch` nie ma `else`?** Samodzielne `else` robiłoby dokładnie to samo co `case @ANYTHING_ELSE`, a dwa sposoby zapisu jednej rzeczy to zbędne zamieszanie: trzeba by pilnować, żeby nie użyć obu naraz. Jeden znacznik działa wszędzie tak samo, sam albo na liście. `else` zostaje w `if`, gdzie nie ma konkurencji.

> **Dlaczego `@` i wielkie litery?** `@ANYTHING_ELSE` nie jest wartością, tylko znacznikiem zmieniającym znaczenie całej gałęzi. Wielkie litery sprawiają, że przy przeglądaniu kodu od razu widać, która gałąź przejmuje nieobsłużone wartości, a `@` odróżnia znacznik od wartości `ENUM` na tej samej liście: w `case ZIELONY, NIEBIESKI, @ANYTHING_ELSE` widać od razu, co jest wartością, a co nie. W C podobny efekt daje `case 10: default:` jeden pod drugim, ale działa tylko dzięki „przelatywaniu” między etykietami, którego BEMOL nie ma.

**Nakładające się wartości: pierwsza pasująca gałąź wygrywa** (kolejność od góry do dołu). Kompilator i tak przypisuje każdą wartość do gałęzi podczas kompilacji, więc nie kosztuje to nic. Ostrzeżenia:

- **szczególny przypadek przed ogólnym** (`case 5`, potem `case 1 to 10`): ostrzeżenie informacyjne, że 5 należy do obu gałęzi i wykona się pierwsza. Często to celowy wzorzec,
- **gałąź martwa** (`case 1 to 10`, potem `case 5`): mocniejsze ostrzeżenie, że `case 5` nigdy się nie wykona. Prawie zawsze to pomyłka.

**Kompletność przy `ENUM`:** gdy `switch` na wyliczeniu nie obsługuje wszystkich wartości i nie ma `@ANYTHING_ELSE`, kompilator ostrzega: „brak obsługi wartości GORACO”. Po dodaniu nowej wartości do wyliczenia kompilator wskaże wszystkie miejsca do uzupełnienia.

Ostrzeżenie, które programista uznaje za zamierzone, potwierdza jawnie przez `@ACCEPT` (sekcja 20).

> **Dlaczego `case` nie „przelatuje” dalej?** W C, C++ i Javie po wykonaniu gałęzi program przechodzi do następnej, chyba że programista napisze `break`. Zapomniany `break` to jeden z najczęstszych błędów w tych językach, a celowe przelatywanie zdarza się rzadko. W BEMOL-u każda gałąź kończy się sama, a kilka wartości dla jednej gałęzi zapisuje się jawnie: `case 1, 2`.

> Jak to działa w środku: [bemol-wnetrze.md, rozdział 12 (`switch` jako tablica skoków)](bemol-wnetrze.md#12-switch-tablica-skoków)

---

## 5. Typy, rozmiary i arytmetyka

Rozmiary są stałe i zdefiniowane przez język, niezależnie od procesora.

| Rodzaj | Typ | Rozmiar |
|---|---|---|
| bit | `bit` | 1/8 bajta |
| bez znaku | `byte` = `unsigned_8` | 1 B |
| | `unsigned_16` | 2 B |
| | `unsigned_32` | 4 B |
| | `unsigned_64` | 8 B |
| ze znakiem | `shortint` = `signed_16` | 2 B |
| | `int` = `signed_32` | 4 B |
| | `longint` = `signed_64` | 8 B |
| zmiennoprzecinkowe | `halffloat` | 2 B |
| | `float` | 4 B |
| | `doublefloat` | 8 B |
| struktura | `STRUCT` | suma pól, zaokrąglona do pełnego bajtu (sekcja 16) |

Nazwy `byte`, `shortint`, `int` i `longint` to wygodne nazwy najczęstszych przypadków ogólnej reguły `unsigned_N` / `signed_N`. Poza tym język nie ma synonimów typów (np. nie ma `integer` obok `int`), żeby kod w jednym projekcie wyglądał jednolicie.

### Typy o dowolnej liczbie bitów: `unsigned_N` i `signed_N`

Dla dowolnego **N od 1 do 64**:

```
zmienna as unsigned_14       # wartości 0–16383
probka as signed_24          # dźwięk 24-bitowy: -8 388 608 – 8 388 607
```

- **jako zmienna**: zajmuje w pamięci tyle pełnych bajtów, ile potrzeba (`unsigned_14` zajmuje 2 bajty, `signed_24` 3 bajty), ale przyjmuje tylko wartości ze swojego zakresu i zawija się na N bitach,
- **w strukturze**: zajmuje dokładnie N bitów (sekcja 16),
- **jako soczewka**: `ptr.unsigned_12[n]` to element nr n, czyli pozycja n × 12 bitów. Działa, ale wolniej, bo elementy nie leżą na granicach bajtów.

Zapis z podkreślnikiem, a nie `unsigned[N]`, bo nawias kwadratowy oznacza pozycję w soczewce: `ptr.unsigned_12[5]` jest jednoznaczne, a `ptr.unsigned[12][5]` nie byłoby.

### Szybkość przetwarzania według szerokości

Procesor ma instrukcje tylko dla szerokości 8, 16, 32 i 64 bitów. Pozostałe szerokości działają poprawnie, ale wymagają dodatkowej pracy:

| Poziom | Szerokości N | Jak procesor to robi | Szybkość |
|---|---|---|---|
| **natywne** | 8, 16, 32, 64 | jedna instrukcja odczytu lub zapisu; pełne wsparcie instrukcji wektorowych (SIMD) | najszybsze |
| **wielokrotność bajtu** | 24, 40, 48, 56 | elementy leżą na granicach bajtów, ale procesor nie ma takiej szerokości: wczytuje więcej bajtów i odcina nadmiar | wolniejsze |
| **pozostałe** | każda inna (1–7, 9–15, 12, 14...) | elementy mogą zaczynać się w środku bajtu: potrzebne przesunięcia bitów i maski | najwolniejsze jako soczewka |

Różnica jest największa przy **soczewkach i operacjach blokowych** na dużych blokach (`ptr.unsigned_12[n]`, `ptr.unsigned_24 += 1`). Pojedyncza zmienna (`x as unsigned_14`) leży w pełnych bajtach, więc kosztuje tylko jedną dodatkową maskę przy zapisie, żeby zawinąć się na N bitach.

Zasada do zapamiętania: **szerokości 8, 16, 32 i 64 są natywne.** Język nie ma dla nich osobnych nazw (np. `fast_16`), bo byłyby to synonimy bez nowej treści. Zamiast tego środowisko programistyczne może wyróżniać szerokości natywne (np. kolorem) i podpowiadać przy nienatywnych, a kompilator w kompilacji testowej zgłasza informację (nie ostrzeżenie), gdy operacja blokowa na dużym bloku używa szerokości nienatywnej.

**Zalecenie:** gdy liczy się szybkość, a format danych nie jest narzucony, wybieraj szerokości natywne. Szerokości nietypowe są dla danych, które już mają taki format (surowe zdjęcia 12-bitowe, dźwięk 24-bitowy, pola bitowe w strukturach). Częstym rozwiązaniem jest wczytanie danych nietypowych raz, zamiana na typ natywny (np. `unsigned_12` → `unsigned_16`), przetworzenie i zapisanie z powrotem.

**Nazwa typu w wyrażeniu liczbowym oznacza jego rozmiar w bajtach:**

```
ptr.new[1024*float]          # 4096 bajtów
img.new[1920*1080*Color]     # struktury też mają rozmiar
```

**Najmniejsza jednostka przydziału pamięci to 1 bajt:**

- w wyrażeniach rozmiaru wynik z bitami zaokrągla się w górę: `new[100*bit]` = 13 bajtów,
- pojedyncza zmienna `b as bit` zajmuje w pamięci cały bajt, ale przyjmuje tylko wartości 0/1 (tożsame z `false`/`true`).

Do oszczędnego przechowywania wielu flag służy blok i soczewka `.bit`: `flagi.new[1000*bit]` zajmuje 125 bajtów.

### Arytmetyka: dwie zasady

**Z1. Liczymy na dużym stole: 64 bity.** Każde działanie na liczbach całkowitych odbywa się na 64 bitach (`longint`; gdy w działaniu bierze udział `unsigned_64`, na 64 bitach bez znaku). Gdy w działaniu jest choć jedna liczba zmiennoprzecinkowa, całe działanie liczone jest w `doublefloat`. Określa to język, a nie procesor: na procesorze 32-bitowym kompilator liczy parami rejestrów (wolniej), ale wynik jest identyczny.

**Z2. Worek decyduje przy wrzucaniu.** Wynik jest dopasowywany do typu zmiennej lub soczewki dopiero przy zapisie: liczba całkowita **zawija się** (zostaje tyle najmłodszych bitów, ile mieści typ), a ułamek jest **odcinany** (sekcja „Zamiana float na typ całkowity”). Z `saturate( )` wynik zatrzymuje się na suficie lub podłodze typu zamiast się zawijać.

```
a, b as byte = 200

suma as int = a + b                  # 400
maly as byte = a + b                 # 400 → zawija się do 144
srednia as byte = (a + b) / 2        # 400 / 2 = 200: po drodze nic się nie zawija
if a + b > 255 then                  # prawda: porównanie na stole
wynik as int = 7.9 + 0.5             # 8.4 → 8 (ułamek odcięty dopiero przy zapisie)

duzy as int
duzy = 2147483647 + 1                # → -2147483648
```

**Przepełnienie worka nie jest błędem**, tylko zachowaniem zdefiniowanym i przewidywalnym. Programista zna pojemność swoich zmiennych, więc świadome zawinięcie jest jego decyzją. Brak sprawdzania oznacza zero kosztu przy każdym działaniu. Dla typów zmiennoprzecinkowych przepełnienie daje nieskończoność, zgodnie ze standardem procesora. Przepełnienie samego stołu (wynik pośredni poza 64 bitami) również się zawija.

> **Dlaczego stół ma 64 bity, a nie rozmiar worka?** Tak liczy procesor: rejestry mają 64 bity, a bajty są do nich rozszerzane przed działaniem. Liczenie „w worku” wymagałoby dokładania po każdym kroku instrukcji obcinających, czyli byłoby wolniejsze i dawało zaskakujące wyniki: średnia pikseli 200 i 200 wychodziłaby 72. Tam, gdzie wynik jest identyczny (`+`, `-`, `*`, operacje bitowe i przesunięcie w lewo), kompilator liczy w wąskim typie, więc operacje blokowe na bajtach nadal korzystają z instrukcji wektorowych przetwarzających 32 bajty naraz.

**`.rangeError` nie dotyczy zmiennych statycznych**, tylko bloków (sekcja 19).

### Nasycenie: `saturate( )`

Gdy programista nie chce zawijania, może jawnie użyć `saturate( )`. Zamiast „przekręcić” wartość na drugą stronę, nasycenie zatrzymuje ją na **suficie** albo **podłodze** zakresu. **`saturate` nasyca w granicach worka**, czyli typu zmiennej albo soczewki, do której trafia wynik. Gdy worka nie ma (porównanie), nasyca w granicach najszerszego typu składników.

| Typ | Podłoga | Sufit |
|---|---|---|
| bez znaku (`byte`, `unsigned_N`) | 0 (same zera) | same jedynki, np. 255 dla `byte` |
| ze znakiem (`shortint`, `int`, `signed_N`) | najmniejsza liczba ujemna, np. -32768 | największa dodatnia, np. 32767 |
| zmiennoprzecinkowe | najmniejsza skończona liczba | największa skończona liczba (zamiast nieskończoności) |

Dla typów ze znakiem sufit to nie same jedynki, bo w zapisie ze znakiem same jedynki oznaczają -1.

```
jasnosc as byte
jasnosc = saturate(ptr.byte[5] + 60)              # jeden element
ptr.byte = saturate(ptr.byte + 60)                # rozjaśnienie całego obrazu bez „przekręcania” jasnych pikseli
if saturate(ptr.byte[5] + ptr.byte[3]) > 100 then # nasycana jest suma, przed porównaniem
```

`saturate` obejmuje **działanie**, a nie porównanie: przy bajtach 200 i 200 suma bez `saturate` zawija się do 144, a z `saturate` daje 255.

Procesory mają gotowe instrukcje wektorowe nasycenia dla bajtów i liczb 16-bitowych, więc w operacjach blokowych na grafice jest to bardzo szybkie.

> **Uwaga dla znających HLSL / Unreal Engine:** w HLSL `saturate(x)` zawsze przycina do zakresu 0–1. W BEMOL-u `saturate( )` przycina do zakresu typu soczewki: `saturate(1.7)` jako `float` zostaje 1.7. Przycięcie do dowolnego zakresu (np. 0–1) to kandydat do biblioteki standardowej: `clamp(x, min, max)`.

### Jawna zamiana typu: `as`

`wyrażenie as typ` zamienia wartość na podany typ, dokładnie tak, jak przypisanie do zmiennej tego typu: liczby całkowite się zawijają (zostaje **najmłodsza część**, np. najmłodszy bajt), a przy zamianie float na liczbę całkowitą odrzucany jest ułamek.

```
i as int = 300                       # &012Ch
b as byte = i as byte                # &2Ch = 44 (najmłodszy bajt)

x = (a + b) as byte                  # zamiana całej sumy
y = a + b as byte                    # zamiana tylko b: as wiąże mocniej niż + i *
```

`as` przydaje się w środku wyrażenia, gdy wartość pośrednia ma być zawinięta wcześniej niż przy zapisie do worka (np. suma kontrolna liczona na 8 bitach). To to samo słowo, które w deklaracjach znaczy „jako typ” (`i as int`), więc ma jedno znaczenie w dwóch miejscach.

> **Dlaczego nie `(byte) i` jak w C?** W BEMOL-u nazwa typu w wyrażeniu oznacza jego rozmiar (`new[100*Color]`). Zapis z nawiasami byłby dwuznaczny: `(Color) - 1` to zamiana liczby -1 na typ `Color` czy rozmiar `Color` minus 1? C rozwiązuje podobne dwuznaczności regułami, które zna niewielu programistów. `as` stoi po wartości, więc dwuznaczności nie ma.

### Zamiana float na typ całkowity

Brana jest **część całkowita, ułamek jest odrzucany** (obcinanie w stronę zera):

```
wynik as int
wynik = 3.7       # 3
wynik = -3.7      # -3
```

Gdy część całkowita jest za duża dla typu, zostaje tyle, ile się mieści. Ułamek jest odcinany dopiero przy zapisie do worka (Z2), więc `wynik = 7.9 + 0.5` daje 8.

### Wyliczenia: `ENUM`

```
ENUM Stan { ZIMNO, CIEPLO, GORACO }                   # wartości 0, 1, 2
ENUM Kanal as byte { R = 0, G = 1, B = 2, A = 3 }     # jawny typ i wartości
```

- **wartości** domyślnie rosną od 0, ale można je podać jawnie (przydatne przy formatach plików),
- **typ** można podać jawnie (`as byte`). Bez tego kompilator wybiera najmniejszy typ bez znaku (`byte`, `unsigned_16`, ...), w którym mieszczą się wszystkie wartości. Wyliczenie ma więc szerokość i działa też jako soczewka: `ptr.Kanal[5]`,
- **użycie:** pełna nazwa `Stan.GORACO`, a tam, gdzie typ jest oczywisty (przypisanie do zmiennej typu `Stan`, `case`), wystarczy samo `GORACO`,
- `switch` na wyliczeniu sprawdza kompletność (sekcja 4).

```
s as Stan = GORACO
switch s
    case ZIMNO
        ...
    case CIEPLO, GORACO
        ...
switch.end
```

### Teksty

Typ `text` to blok pamięci przechowujący tekst UTF-8. Opis: sekcja 18.

---

## 6. Literały

**Literał** to wartość zapisana wprost w kodzie. Jego szerokość jest zawsze znana podczas kompilacji.

**Szerokość literału to liczba cyfr razy kwant jego systemu liczbowego:**

| System | Zapis | Kwant | Przykład | Szerokość |
|---|---|---|---|---|
| binarny | `&...b` | 1 bit na cyfrę | `&101b` | 3 bity |
| szesnastkowy | `&...h` | 4 bity na cyfrę | `&FF0ACh` | 20 bitów |
| dziesiętny | zwykła liczba | pełne bajty | `5` | 1 bajt |

- **Zera wiodące się liczą**, bo decyduje zapis, a nie wartość: `&0Fh` to 8 bitów, `&00FFh` to 16 bitów.
- **Długość literału wyznacza wzór w `.fill` bez soczewki** (`ptr.fill[&101b]` powtarza 3 bity). Przy zapisie przez soczewkę literał jest zwykłą liczbą: o szerokości decyduje soczewka (sekcja 10).
- Wartość leży w pamięci w porządku little-endian: najmniej znacząca część trafia na najniższą pozycję. `ptr.unsigned_16[0] = &FF00h` daje bajt 0 = `00`, bajt 1 = `FF`.

> **Kolejność bajtów w przykładach:** w całej specyfikacji zawartość pamięci pokazywana jest **w kolejności adresów, od bajtu 0**. Liczba `&0100h` (256) leży więc w pamięci jako `00 01`: bajt 0 = `00` (mniej znaczący), bajt 1 = `01`. Czytając tę samą liczbę jak zapis binarny, od prawej do lewej, widzimy `01 00`. Obie formy opisują te same dane.

**Literał dziesiętny nie ma własnej szerokości.** Przyjmuje typ worka, do którego trafia (zmiennej albo soczewki), i jest liczony na stole jak każda liczba (sekcja 5). Liczba z ułamkiem (`1.5`) to `doublefloat`.

Tam, gdzie nie ma worka, który wyznaczyłby szerokość (np. `ptr.fill[5]` bez soczewki), literał dziesiętny to **błąd kompilacji** z podpowiedzią: `ptr.byte.fill[5]` albo `ptr.fill[&05h]`. Szerokość jest wtedy widoczna w zapisie, a nie ukryta w wartości liczby.

> **Dlaczego literał dziesiętny nie ma szerokości?** Gdyby szerokość wynikała z wartości, `ptr.fill[255]` powtarzałoby wzór 1-bajtowy, a `ptr.fill[256]` wzór 2-bajtowy: zmiana liczby o 1 zmieniałaby wynik całego bloku. Literał szesnastkowy i binarny niesie szerokość w samym zapisie (`&00FFh` to 16 bitów), więc tam nie ma czego zgadywać.

---

## 7. Typ `pointer`

`pointer` to zmienna wskazująca na blok pamięci przydzielany dynamicznie. Daje dostęp do każdego bajtu i bitu bloku i jest objęta automatycznym zarządzaniem pamięcią.

```
ptr as pointer
GLOBAL ptr as pointer
```

Zadeklarowana zmienna nie ma jeszcze bloku: `ptr.size` zwraca 0.

### Przypisanie wskaźnika a zapis danych

```
cel = zrodlo                                       # zmienna = zmienna: kopia WSKAŹNIKA
kafelek = obraz.viewRectangle[...]                 # zmienna = widok: kopia WSKAŹNIKA (nowy widok)
cel.viewPortion[0:400] = zrodlo.viewPortion[...]   # widok = widok: kopia DANYCH
ptr.byte[5] = x                                    # soczewka = wartość: zapis DANYCH
```

**Reguła: gdy po lewej stoi sama zmienna, przypisujemy wskaźnik. Gdy po lewej stoi fragment bloku (soczewka lub widok), zapisujemy dane.**

**Przypisanie wskaźnika** (`ptr2 = ptr`) kopiuje tylko wskaźnik: obie zmienne wskazują ten sam blok, a jego `.shares` rośnie o 1. Kopię danych tworzą wyłącznie operacje `copy...` albo przypisanie widoku do widoku.

Gdy zmienna `pointer` dostaje nowy blok (np. `glb = mojaFunkcja()`), `.shares` jej poprzedniego bloku maleje o 1, a pamięć jest zwalniana, gdy licznik spadnie do 0.

### Wskaźnik zapisany w bloku to zwykła liczba

Jeśli programista zapisze wskaźnik do wnętrza surowego bloku (`a.unsigned_32[0] = b`), w bloku ląduje tylko numer wpisu. Blok nie wie, że te bajty są wskaźnikiem, więc **nie zwiększa to `.shares`** i nie chroni bloku `b` przed zwolnieniem. Za poprawność takiej liczby odpowiada programista, tak jak w asemblerze.

Dzięki temu **bloki nigdy nie tworzą cykli** (A trzyma B, a B trzyma A), a licznik `.shares` zawsze w końcu spada do zera.

---

## 8. Cykl życia bloku

### `.new` — rejestracja

**Rejestruje zmienną w menedżerze pamięci** i przydziela pierwszy blok. Można jej użyć **tylko raz w życiu zmiennej**. Rozmiar podaje się w bajtach lub jako `ilość*typ`.

**`.new` nie zeruje bloku.** Zawartość nowego bloku jest nieokreślona (chyba że włączono wzór pamięci, patrz niżej).

```
ptr.new[1024]
ptr.new[100*int]
ptr.clear                  # jawne zerowanie, gdy jest potrzebne
```

**Deklaracja z przydziałem w jednej linii**, tak jak `x as int = 5` dla liczb:

```
blok as pointer.new[1024]          # to samo co: blok as pointer  +  blok.new[1024]
```

Skrót jest dozwolony tylko w deklaracji i działa dokładnie jak `.new`: rejestruje zmienną i przydziela blok bez zerowania.

### `.update` — zmiana rozmiaru

Zmienia rozmiar bloku, **zachowując istniejące dane**. **Nowo dodane bajty nie są zerowane**: ich zawartość jest nieokreślona. Po `.release` przydziela nowy blok o nieokreślonej zawartości.

Powód: przy bardzo dużych blokach zerowanie to kosztowna operacja, często zbędna, bo programista i tak zaraz wypełni blok własnymi danymi. Kto potrzebuje zer, mówi to jawnie:

```
stary as longint = ptr.size
ptr.update[2048]
ptr.viewPortion[stary:ptr.size-stary].clear    # zeruje tylko nowo dodaną część
```

**Pamięć obiecana a pamięć przydzielona.** System operacyjny po `.new` i `.update` tylko *obiecuje* pamięć: zapisuje, że blok istnieje, ale fizyczne strony (po 4 KB) podpina dopiero przy pierwszym zapisie do każdej z nich. Dlatego duży blok po `.update` prawie nic nie kosztuje, a pamięć programu rośnie dopiero w miarę zapisywania danych. Program, który musi mieć pamięć przydzieloną od razu (część krytyczna, praca, której nie wolno przerwać w połowie), dotyka całego bloku jawnie:

```
dane.update[3000000000]
dane.clear                 # każda strona dostaje fizyczną pamięć teraz, a nie w trakcie pracy
```

Kompilator nigdy nie usuwa tego `.clear` jako „zbędnego” (sekcja 22), choć świeże strony od systemu i tak są zerami.

> **Dlaczego `.update` nie przydziela pamięci od razu?** Wiele programów rezerwuje blok „na zapas” (bufor na plik o nieznanej długości, obraz, który może urosnąć) i używa tylko jego części. Przydzielanie wszystkiego od razu kosztowałoby czas i pamięć wszystkie takie programy. W BEMOL-u koszt ponosi tylko ten, kto go jawnie wybrał, a w kodzie widać, który blok jest przydzielony od razu.
>
> Różnica między systemami: Windows liczy obietnice ściśle, więc za duże `.update` dostaje odmowę od razu i program kończy się czytelnym błędem `BML-E0003 Brak pamięci` w tej linii. Linux zwykle obiecuje więcej, niż ma; brak pamięci wychodzi tam dopiero przy zapisie, a `.clear` zaraz po `.update` przenosi ten moment na początek pracy.

### `.release` — zwolnienie pamięci

Zwalnia blok i ustawia `.size` na 0. **Rejestracja zmiennej przeżywa `.release`**: inna część programu, która trzyma tę zmienną, nie dostaje wskaźnika donikąd, tylko widzi `.size = 0`, a odczyt zachowuje się zgodnie z `.rangeError`.

**Bloku, na który patrzą widoki, nie można zwolnić** (sekcja 14). Najpierw trzeba zwolnić widoki.

```
.new  ──►  [ .update  ⇄  .release ]  ──►  koniec życia zmiennej
(raz)       (dowolnie wiele razy)
```

### Wzory pamięci (pomoc przy szukaniu błędów)

Odczyt bajtów, których program nigdy nie zapisał, to klasyczny, trudny do znalezienia błąd. Żeby go wychwycić, nowe bajty (przy `.new` i przy powiększeniu przez `.update`) można automatycznie wypełniać rozpoznawalnym wzorem. Jeśli w danych pojawią się wartości `CDCDCDCD`, od razu widać, że program czyta coś, czego nie zapisał.

Wzory są **osobne dla kompilacji testowej i dla finalbake** i **oba są domyślnie wyłączone**, żeby nawet podczas rozwijania programu nie wpływały na wydajność. Programista musi je świadomie włączyć.

**Ustawienia dla całego programu:**

```
DEFAULT_MEMORY_PATTERN_DEBUG = ON          # domyślnie OFF
DEFAULT_MEMORY_PATTERN_PRODUCTION = ON     # domyślnie OFF

MEMORY_PATTERN_DEBUG_BYTE = &CDh           # domyślnie &CDh
MEMORY_PATTERN_PRODUCTION_BYTE = &00h      # domyślnie &00h
```

- **wzór debug** (`&CDh`) służy do rozpoznawania niezapisanych danych podczas testów,
- **wzór produkcyjny** (`&00h`) służy bezpieczeństwu w gotowym programie: nowy blok nie zawiera resztek poprzednich danych (np. haseł).

**Ustawienia dla konkretnej zmiennej** (nadpisują domyślne):

```
ptr.memoryPatternDebug = ON
ptr.memoryPatternProduction = OFF
```

**Działanie:** przy `.new` menedżer odczytuje ustawienia domyślne programu i zapisuje je we flagach wpisu (bity 6 i 7, sekcja 9). Ustawienie lokalne nadpisuje domyślne:

- ustawione **przed `.new`**: kompilator je zapamiętuje i stosuje przy rejestracji,
- ustawione **po `.new`**: działa przy kolejnym `.update`.

**Bajt wzoru jest jeden dla całego programu.** We flagach wpisu jest miejsce tylko na włączone/wyłączone, więc pojedyncza zmienna może jedynie włączyć lub wyłączyć wypełnianie.

Wzory nigdy nie są stosowane do plików mapowanych (sekcja 15), bo nadpisałyby dane z dysku.

### Zmienne `pointer` w funkcjach: `PERSISTENT`

**Zwykła zmienna** dostaje nowy wpis w menedżerze przy każdym wywołaniu funkcji.

**Zmienna `PERSISTENT`** ma w menedżerze zarezerwowany wpis, gotowy przy każdym wywołaniu funkcji. Oszczędza to koszt rejestracji w funkcjach wywoływanych bardzo często. **Adres i zawartość bloku nie są gwarantowane** między wywołaniami: trwałe jest miejsce w menedżerze, nie dane. Nazwa nawiązuje do *persistent level* w Unreal Engine: stale obecne jest miejsce, a jego zawartość się zmienia.

```
FUNCTION przetwarzaj()
    everyTimeNew as pointer
    PERSISTENT onceAndFast as pointer
przetwarzaj.end
```

**Na końcu funkcji sprawdzane jest `.shares` bloku `PERSISTENT`:**

- **0**: blok był używany tylko w funkcji, wpis jest czyszczony i czeka na kolejne wywołanie,
- **większe od 0**: blok „uciekł” z funkcji (zwrócony, przypisany do zmiennej globalnej). Odłącza się od trybu `PERSISTENT` i staje zwykłym blokiem nowego właściciela, a funkcja dostanie nowy wpis przy następnym wywołaniu.

**Rekurencja:** gdy wpis `PERSISTENT` jest zajęty przez trwające wywołanie, kolejne wywołanie dostaje zwykły blok. `PERSISTENT` to optymalizacja, więc w trudnym przypadku z niej rezygnuje, a program działa poprawnie.

> Jak to działa w środku: [bemol-wnetrze.md, rozdział 7 (`PERSISTENT` w praktyce)](bemol-wnetrze.md#7-persistent-w-praktyce)

---

## 9. Menedżer pamięci

### Tablica przydziałów

Menedżer pamięci to **tablica dynamiczna**, w której każdy wiersz opisuje jeden przydział. **Numer wiersza jest identyfikatorem bloku**: zmienna `pointer` przechowuje tylko ten numer (4 bajty). Dostęp do wpisu jest natychmiastowy (początek tablicy + numer × 32). Numery po zwolnionych przydziałach są ponownie wykorzystywane dzięki liście wolnych miejsc.

| Przesunięcie | Pole | Rozmiar | Opis |
|---|---|---|---|
| 0 | adres | 8 B | położenie bloku w pamięci |
| 8 | długość | 8 B | rozmiar bloku w bajtach (do 2^64 B ≈ 16 milionów TB) |
| 16 | shares | 4 B | liczba zmiennych trzymających blok |
| 20 | flagi | 2 B (16 bitów) | cechy serwisowe bloku, tabela poniżej |
| 22 | liczba widoków | 2 B | ile widoków patrzy na ten blok (do 65 535) |
| 24 | pole zależne od rodzaju wpisu | 8 B | znaczenie wyznacza flaga, tabela poniżej |

**Wpis ma 32 bajty.** Pola leżą w naturalnym porządku, bez dziur. To potęga dwójki, więc procesor znajduje wpis jednym przesunięciem bitowym, a w jednej linii pamięci podręcznej (64 B) mieszczą się dokładnie dwa wpisy. Milion jednoczesnych bloków to 32 MB.

### Pole zależne od rodzaju wpisu

Ostatnie 8 bajtów wpisu (przesunięcie 24) ma znaczenie zależne od rodzaju wpisu, który wyznacza flaga:

| Rodzaj wpisu | Przesunięcie 0 (8 B) | Przesunięcie 8 (8 B) | Przesunięcie 24 (8 B) |
|---|---|---|---|
| zwykły blok | adres | długość | zarezerwowane (np. w przyszłości numer maszyny w klastrze) |
| `TEXT` | adres | **pojemność** | **długość tekstu** (sekcja 18) |
| `VIEW` | przesunięcie w rodzicu | długość widoku | numer rodzica (4 B) + numer opisu prostokąta (4 B) (sekcja 14) |

**Flagi korzystające z tego pola wykluczają się nawzajem**: wpis jest albo tekstem, albo widokiem, nigdy jednym i drugim. Pozostałe flagi (np. `MAPPED`) pola nie używają, więc mogą łączyć się z dowolnym rodzajem: tekst wczytany przez `.map` ma naraz `TEXT` i `MAPPED`. Każdy przyszły rodzaj wpisu musi odpowiedzieć na pytanie, czy potrzebuje tego pola i czy nie koliduje z innymi.


Gdy `.update` musi przenieść blok w inne miejsce, zmienia się tylko adres we wpisie. Wszystkie zmienne i widoki wskazujące ten przydział od razu widzą nowy adres.

**Wolny wpis** rozpoznaje się po `.shares` = 0 **i** liczbie widoków = 0. Zmienna po `.release` ma `.shares` > 0 (nadal ktoś ją trzyma) i `.size` = 0.

### Flagi wpisu (bity serwisowe)

| Bit | Flaga | Znaczenie |
|---|---|---|
| 0 | `GLOBAL` | blok należy do zmiennej globalnej |
| 1 | `PERSISTENT` | zarezerwowany wpis zmiennej `PERSISTENT` w funkcji |
| 2 | `VIEW` | wpis jest widokiem na inny blok (sekcja 14) |
| 3 | `MAPPED` | blok to plik podpięty przez `.map` (sekcja 15) |
| 4 | `MAPPED_WRITABLE` | plik mapowany otwarty do zapisu (ma sens tylko razem z `MAPPED`) |
| 5 | `TEXT` | blok przechowuje tekst (sekcja 18) |
| 6 | `DEBUG_MEMORY_PATTERN` | wypełnianie nowych bajtów wzorem w kompilacji testowej |
| 7 | `PRODUCTION_MEMORY_PATTERN` | wypełnianie nowych bajtów wzorem w finalbake |
| 8 | `rangeError`, bit młodszy | tryb wyjścia poza blok (sekcja 19) |
| 9 | `rangeError`, bit starszy | |
| 10–15 | — | wolne |

Używanych jest 10 z 16 bitów, a 6 (bity 10–15) zostaje na przyszłe cechy.

**Tryb `rangeError`** zapisany jest na dwóch bitach: wartość = bit 9 × 2 + bit 8, czyli 0 = `DEFAULT`, 1 = `CONTINUE`, 2 = `WARNING`, 3 = `HALT`. Wartość 0 oznacza „sprawdź ustawienie domyślne programu” (`DEFAULT_RANGE_ERROR`).

### Liczba użyczeń `.shares`

- gdy element programu (funkcja, pętla, program główny) zaczyna używać bloku, `.shares` rośnie o 1,
- przypisanie `ptr2 = ptr` zwiększa `.shares` o 1,
- gdy element programu się kończy, `.shares` maleje o 1,
- widoki **nie** zmieniają `.shares` rodzica, tylko jego **liczbę widoków** (sekcja 14),
- **pamięć jest zwalniana automatycznie, gdy `.shares` = 0 i liczba widoków = 0.**

Każdy licznik mówi jedną rzecz: `.shares` to liczba zmiennych trzymających blok, a liczba widoków to liczba widoków na niego patrzących.

Zmienna `GLOBAL` należy do programu głównego, więc jej `.shares` nie spadnie do 0 przed końcem programu. Pamięć można zwolnić wcześniej ręcznie, przez `.release`.

> Jak to działa w środku: [bemol-wnetrze.md, rozdział 1 (menedżer bloków bajt po bajcie)](bemol-wnetrze.md#1-menedżer-bloków)

---

## 10. Soczewki: pozycja i szerokość

Każdy dostęp do bloku przez soczewkę (`ptr.<typ>[n]`) rozstrzyga dwie rzeczy: **gdzie** zaczynamy i **ile** czytamy lub zapisujemy.

### Pozycja: wyznacza soczewka

Indeks to przesunięcie **w jednostkach typu soczewki**, liczone od zera. Każdy typ liczy w swoich jednostkach, bez wyjątków:

```
ptr.Color[32]     # 32 × Color (10 B) = bajt 320
ptr.int[4]        # 4 × int (4 B)     = bajt 16
ptr.byte[7]       # 7 × byte (1 B)    = bajt 7
ptr.bit[1]        # 1 × bit           = bit 1
```

### Szerokość: wyznacza soczewka

**Z3. Soczewka czyta i pisze zawsze swoją szerokość.** `.byte` to zawsze 1 bajt, `.unsigned_16` zawsze 2 bajty, `.Color` zawsze 10 bajtów, bez względu na to, co stoi po drugiej stronie. Odczytana wartość trafia na stół jak każda liczba (sekcja 5), a zapisywana wartość jest dopasowywana do soczewki jak do worka: zawija się albo, z `saturate`, nasyca.

```
licznik as int = 300
d as doublefloat

x as int = ptr.byte[5]             # odczyt 1 bajtu
ptr.byte[i] = licznik              # zapis 1 bajtu: 300 → 44 (najmłodszy bajt)
if ptr.byte[5] > licznik then      # odczyt 1 bajtu, porównanie na stole
ptr.byte[i] = 0                    # zapis 1 bajtu
if ptr.int[78] > 5 then            # odczyt 4 bajtów od bajtu 312
suma = ptr.byte[5] + ptr.byte[6]   # każda soczewka po 1 bajcie
wynik.Color[0] = obraz.Color[17]   # przeniesienie całego piksela (10 B)
```

**Z4. Dowolny typ od dowolnego bajtu: `.at`.** Soczewka z `.at[n]` liczy pozycję **w bajtach**, a nie w swoich jednostkach. Tak czyta się i zapisuje wartości leżące w nietypowym miejscu, np. w nagłówkach plików:

```
d = ptr.doublefloat.at[1009]       # 8 bajtów od bajtu 1009
ptr.doublefloat.at[1009] = d       # zapis 8 bajtów (1009–1016)
ptr.unsigned_32.at[3] = rozmiar    # 4 bajty od bajtu 3
```

Typ i pozycję widać w zapisie: `ptr.doublefloat.at[1009]` czyta się „liczba `doublefloat` od bajtu 1009”.

**Z5. Literał to zwykła liczba, także szesnastkowy i binarny.** Przy zapisie przez soczewkę zawija się do jej szerokości jak każda wartość (Z2). Gdy stały literał ma więcej bitów niż soczewka, kompilator zgłasza **ostrzeżenie** („literał 16-bitowy obcięty do 8 bitów soczewki `.byte`”), bo zwykle to literówka albo zła soczewka:

```
a.byte[0] = &1234h                 # bajt 0 = 34, ostrzeżenie o obcięciu
a.byte = &1234h                    # każdy bajt = 34, to samo ostrzeżenie
a.unsigned_16[0] = &1234h          # bajty 0–1: 34 12
a.unsigned_16.at[1] = &1234h       # bajty 1–2: 34 12
a.byte[0] = &1234h as byte         # jawne obcięcie: bez ostrzeżenia
a.byte[0] = wartosc                # zmienna: zawija się bez ostrzeżenia
```

Obcięcie bywa zamierzone („odfiltrowanie” części wartości). Wtedy wystarczy `as byte` albo `@ACCEPT WARNING` (sekcja 20). Zapis zmiennej przez węższą soczewkę zawija się bez ostrzeżenia, bo to normalna praca na danych. Do zapisu pojedynczych bitów służą soczewki bitowe (`ptr.bit[3] = 1`, `ptr.unsigned_13[0]`) i pola bitowe struktur.

### Zasady w praktyce: literały i zmienna

Zmienna `v as unsigned_32 = &12345678h`, blok `a as pointer.new[8]` zerowany przed każdym przypadkiem. Bajty pokazane od adresu 0. Wyniki sprawdzone w prototypie tłumacza (`prototyp/przyklady/literaly.bmol`).

| Zapis | Bajty | Dlaczego |
|---|---|---|
| `a.byte[0] = &1234h` | `34 00 00 00 00 00 00 00` | soczewka 1 B, literał obcięty (ostrzeżenie BML-W0120) |
| `a.byte = &12h` | `12 12 12 12 12 12 12 12` | operacja blokowa: każdy bajt osobno |
| `a.unsigned_16[0] = &1234h` | `34 12 00 00 00 00 00 00` | 2 B, little-endian |
| `a.unsigned_16.at[1] = &1234h` | `00 34 12 00 00 00 00 00` | `.at`: pozycja w bajtach |
| `a.unsigned_32[0] = &12h` | `12 00 00 00 00 00 00 00` | krótszy literał uzupełniony zerami do szerokości soczewki |
| `a.fill[&1234h]` | `34 12 34 12 34 12 34 12` | `.fill` bez soczewki: wzór o długości literału |
| `a.byte[0] = v` | `78 00 00 00 00 00 00 00` | najmłodszy bajt zmiennej, bez ostrzeżenia |
| `a.unsigned_16[1] = v` | `00 00 78 56 00 00 00 00` | element nr 1 = bajty 2–3, dwa najmłodsze bajty `v` |
| `a.unsigned_32.at[2] = v` | `00 00 78 56 34 12 00 00` | całe `v` od bajtu 2 |
| `a.unsigned_64[0] = v` | `78 56 34 12 00 00 00 00` | `v` rozszerzone do 8 B |
| `a.byte[0] = v shr 8` | `56 00 00 00 00 00 00 00` | przesunięcie na stole (Z1), potem najmłodszy bajt (Z2) |
| `a.unsigned_16 = v` | `78 56 78 56 78 56 78 56` | każdy element 16-bitowy = `&5678h` |
| `a.fill[v]` | `78 56 34 12 78 56 34 12` | wzór o długości typu zmiennej (4 B) |
| `a.byte` = `FF`, potem `a.byte += 1` | `00 00 00 00 00 00 00 00` | każdy bajt zawija się osobno |

Odczyt, gdy blok zawiera `78 56 34 12 00 00 00 00`:

| Zapis | Wynik | Dlaczego |
|---|---|---|
| `x as unsigned_32 = a.byte[1]` | `&00000056h` | soczewka czyta 1 bajt, choć `x` ma 4 B |
| `y as unsigned_32 = a.unsigned_16[0]` | `&00005678h` | soczewka czyta 2 bajty |
| `z as unsigned_32 = a.unsigned_32.at[1]` | `&00123456h` | 4 bajty od bajtu 1: `56 34 12 00` |

> **Dlaczego soczewka zawsze decyduje o szerokości?** Wcześniejsza wersja reguły pozwalała drugiej stronie wyznaczać szerokość: `x as int = ptr.byte[5]` czytało 4 bajty, a `suma = ptr.byte[5] + ptr.byte[6]` po jednym, więc dopisanie `+ 0` zmieniało wynik. Prototyp tłumacza pokazał też, że naturalne `blok.byte[i] = i` zapisywało 8 bajtów. Teraz `.byte` znaczy zawsze jeden bajt, także przy literałach, a nietypowy dostęp jest jawny dzięki `.at`.

> Jak to działa w środku: [bemol-wnetrze.md, rozdział 3 (obliczanie pozycji w soczewkach)](bemol-wnetrze.md#3-soczewki-obliczanie-pozycji)

---

## 11. Odłamki: niepełne elementy

**Odłamek** powstaje, gdy odczyt lub zapis od wyznaczonej pozycji sięga poza koniec bloku.

**Odczyt:** zmienna docelowa jest najpierw wypełniana zerami, a potem nakładane są na nią bajty istniejące w bloku, zaczynając od najmniej znaczącej części. Brakujące bajty zostają zerami w bardziej znaczącej części.

**Zapis:** do bloku trafiają tylko bajty, które w nim istnieją. Nadmiarowa część wartości jest odrzucana.

W obu przypadkach program reaguje zgodnie z `.rangeError`.

```
ptr.new[1023]                  # bajty 0–1022

x as float
x = ptr.float[255]             # od bajtu 1020: 3 bajty z bloku + 1 bajt zer

d as doublefloat
d = ptr.doublefloat.at[1020]   # od bajtu 1020: 3 bajty z bloku + 5 bajtów zer
ptr.doublefloat.at[1020] = d   # zapisane tylko 3 bajty (1020–1022)

y as float
y = ptr.float[500]             # od bajtu 2000: całkowicie poza blokiem, same zera
```

Odłamek typu `float` zwykle nie ma sensu liczbowego. To błąd założeń programisty (blok o złym rozmiarze). Zalecenie: przydzielaj bloki w jednostkach typu, z którym pracujesz, np. `new[1024*float]`.

> Jak to działa w środku: [bemol-wnetrze.md, rozdział 6 (odłamki w praktyce)](bemol-wnetrze.md#6-odłamki-w-praktyce)

---

## 12. Operacje blokowe

**Soczewka bez indeksu oznacza cały blok** jako ciąg elementów. Operacja wykonuje się na każdym elemencie:

```
ptr.float *= 2                              # każdy float w bloku razy 2
ptr.byte += 1                               # każdy bajt plus 1
ptr.float = 1.5                             # każdy float = 1.5
ptr.viewPortion[0:400].float *= 2           # tylko floaty w widoku
```

Zasada: **bez indeksu = całość, z indeksem = jeden element**.

`ptr.<typ>.count` zwraca liczbę **pełnych** elementów typu w bloku. Ostatni, niepełny element (odłamek) też jest objęty operacją, zgodnie z sekcją 11.

Kompilator zamienia operację blokową na pętlę w kodzie maszynowym, która przetwarza wiele elementów naraz instrukcjami wektorowymi (SIMD).

### Wypełnianie: `.fill`

`.fill[wartość]` wypełnia blok powtarzanym wzorem. Długość wzoru wyznacza soczewka, typ zmiennej albo długość literału szesnastkowego lub binarnego:

```
ptr.float.fill[1.5]      # z soczewką: powtarzany float (4 B)
ptr.fill[kolor]          # zmienna (kolor as Color): powtarzany 10-bajtowy piksel
ptr.fill[&00FFh]         # literał szesnastkowy: powtarzane 16 bitów
ptr.fill[&101b]          # literał binarny: powtarzane 3 bity
ptr.byte.fill[5]         # literał dziesiętny z soczewką: powtarzany 1 bajt
ptr.fill[5]              # błąd: literał dziesiętny bez soczewki nie ma szerokości (sekcja 6)
```

**Wzór jest powtarzany z dokładnością do bitu**, także przez granice bajtów (`&101b` daje `101101101...`). Jeśli długość bloku w bitach nie dzieli się przez długość wzoru, ostatnie powtórzenie jest ucinane, zgodnie z zasadą odłamków.

`.clear` wypełnia cały blok zerami (to samo co `.byte.fill[0]`).

---

## 13. Operacje bitowe i inne operacje wbudowane

### Operacje bitowe

| Operator | Działanie |
|---|---|
| `and`, `or`, `xor`, `not` | operacje logiczne na bitach |
| `shl`, `shr` | przesunięcie bitów w lewo / w prawo |
| `rol`, `ror` | rotacja bitów w lewo / w prawo (bity wypadające z jednej strony wracają z drugiej) |

Rotacje są szczególnie ważne w kryptografii (SHA, ChaCha), a C nie ma na nie operatora.

**Każda operacja działa w ramach soczewki:**

```
x = ptr.unsigned_32[5] and &FF00h     # jeden element
ptr.byte shl= 1                       # każdy bajt osobno: wypadające bity przepadają
ptr.unsigned_32 rol= 7                # każdy element 32-bitowy osobno
ptr.unsigned_32 xor= klucz            # cały blok XOR klucz, element po elemencie
```

### Cały blok jako jedna liczba: `.value`

`.value` to **największa soczewka**: cały blok traktowany jako jedna liczba (little-endian). Przesunięcia i rotacje przenoszą wtedy bity przez granice bajtów:

```
# bajty: [0]=10000001  [1]=00000001
ptr.byte shl= 1       # [0]=00000010  [1]=00000010  (najstarszy bit bajtu 0 przepadł)
ptr.value shl= 1      # [0]=00000010  [1]=00000011  (bit przeszedł do bajtu 1)

dane.viewPortion[16:64].value shr= 5     # tylko fragment bloku jako jedna liczba
```

Soczewka decyduje też, do czego stosowany jest drugi składnik:

```
ptr.byte xor= &FFh      # każdy bajt XOR FF: odwraca wszystkie bity bloku
ptr.value xor= &FFh     # cała liczba XOR FF: odwraca tylko najniższy bajt
```

Zastosowania `.value`: arytmetyka wielkich liczb w kryptografii (RSA na liczbach 2048-bitowych), kompresja (kody o zmiennej długości w ZIP czy JPEG), strumienie bitów.

### Inne operacje wbudowane

Do języka trafia to, co odpowiada jednej instrukcji procesora albo wymaga wiedzy kompilatora, żeby działało szybko. Nazwy do ustalenia (sekcja 28):

- **liczenie bitów:** liczba jedynek, liczba zer od góry i od dołu (kompresja, kryptografia, struktury danych),
- **nasycenie `saturate( )`:** `250 + 10` w bajcie daje `255` zamiast zawinięcia do `4` (grafika: rozjaśnianie, mieszanie kolorów); opis w sekcji 5,
- **redukcje blokowe:** suma, minimum, maksimum, iloczyn skalarny dwóch bloków (podstawa uczenia maszynowego),
- **zamiana kolejności bajtów** dla plików i protokołów zapisanych w big-endian.

---

## 14. Widoki i kopie fragmentów

**Widok** to okno na fragment istniejącego bloku, **bez kopiowania danych**. **Kopia** tworzy nowy, niezależny blok.

| Kształt | Widok (bez kopiowania) | Kopia (nowe dane) |
|---|---|---|
| ciągły fragment | `viewPortion[od:ile]` | `copyPortion[od:ile]` |
| prostokąt | `viewRectangle[x, y, w, h, krok]` | `copyRectangle[x, y, w, h, krok]` |
| cały blok | — | `copy` |

### Jednostki

- `viewPortion` / `copyPortion`: `od` i `ile` w **bajtach**,
- `viewRectangle` / `copyRectangle`: **w poziomie w bajtach** (x, szerokość w, krok = długość wiersza w rodzicu), **w pionie w wierszach** (y, wysokość h).

```
kafelek = obraz.viewRectangle[100*Color, 50, 64*Color, 64, szer*Color]
```

Czyta się: od piksela 100 w wierszu 50, 64 piksele szerokości, 64 wiersze, wiersz obrazu ma `szer` pikseli.

Widok ma wszystkie operacje bloku (soczewki, operacje blokowe, `.size`, `.fill`...) oprócz `.new`.

```
kafelek.Color[0]          # lewy górny piksel wycinka
kafelek.Color *= 1.2      # operacja blokowa tylko na wycinku
```

### Kopiowanie fragmentu do innego bloku

**Przypisanie widoku do widoku kopiuje bajty:**

```
cel.viewPortion[0:400] = zrodlo.viewPortion[1000:400]
miniatura.viewRectangle[0, 0, 64*Color, 64, 64*Color] = obraz.viewRectangle[100*Color, 50, 64*Color, 64, szer*Color]
```

- widok docelowy wyznacza, ile bajtów zostanie zapisanych,
- jeśli źródło jest krótsze, brakujące bajty są uzupełniane zerami,
- jeśli zapis wychodzi poza blok docelowy, nadmiar jest odrzucany,
- w obu przypadkach reaguje `.rangeError`,
- **gdy fragmenty nachodzą na siebie** w tym samym bloku, wynik jest taki, jakby najpierw skopiowano całe źródło, a potem je zapisano.

Kompilator zamienia to na najszybsze kopiowanie pamięci, jakie ma procesor. Prostokąty są kopiowane wiersz po wierszu.

### Widoki w menedżerze pamięci

Każdy widok ma **własny wpis w menedżerze bloków** (flaga `VIEW`). Widok nie ma własnej pamięci ani zapasu, więc pola wpisu mają inne znaczenie:

| Przesunięcie | Zwykły blok | Widok (`VIEW`) |
|---|---|---|
| 0 (8 B) | adres | przesunięcie w rodzicu (w bajtach) |
| 8 (8 B) | długość | długość widoku |
| 16 (4 B) | shares | shares widoku |
| 20 (2 B) | flagi | flagi |
| 22 (2 B) | liczba widoków | 0 (widok widoku jest spłaszczany, patrz niżej) |
| 24 (4 B) | zarezerwowane | **numer rodzica**: numer wiersza rodzica w tablicy menedżera bloków |
| 28 (4 B) | zarezerwowane | **numer opisu prostokąta** (0 = widok paskowy, bez opisu) |

**`viewPortion` to sam wpis**: rodzic, przesunięcie i długość mieszczą się w nim w całości.

**`viewRectangle` ma dodatkowo 16-bajtowy opis** w osobnej tablicy opisów prostokątów:

| Pole opisu | Rozmiar | Znaczenie |
|---|---|---|
| bajty wiersza | 8 B | szerokość jednego wiersza widoku |
| krok | 8 B | odległość między początkami wierszy w rodzicu |

Liczba wierszy nie jest zapisywana, bo wynika z długości: wiersze = długość / bajty wiersza.

**Dostęp do bajtu nr k widoku:**

- widok paskowy: adres = adres rodzica + przesunięcie + k,
- widok prostokątny: wiersz = k / bajty wiersza, kolumna = k % bajty wiersza, adres = adres rodzica + przesunięcie + wiersz × krok + kolumna.

Adres rodzica jest odczytywany z jego wpisu (raz przed pętlą). Widok pamięta numer rodzica, a nie adres, więc po przeniesieniu rodzica przez `.update` nadal wskazuje właściwe miejsce. W pętli kompilator nie dzieli przy każdym dostępie, tylko przechodzi wiersz po wierszu i na końcu wiersza przeskakuje o krok. Przykład krok po kroku: [bemol-wnetrze.md, rozdział 5](bemol-wnetrze.md#5-widoki-krok-po-kroku).

**Widok widoku** jest przy tworzeniu zamieniany na widok bezpośrednio na oryginalny blok (przesunięcia się sumują), więc dostęp to zwykle jeden poziom, bez łańcucha pośredników.

**Wyjątek: widok paskowy na widoku prostokątnym** (np. `kafelek.viewPortion[0:20]`). Pasek może obejmować kilka wierszy prostokąta, więc nie da się go zapisać jako jednego widoku na oryginalny blok. Jego rodzicem zostaje wtedy widok prostokątny, a adres liczony jest w dwóch krokach (najpierw w prostokącie, potem w bloku). Wykazał to prototyp tłumacza.

### Zasady życia widoków

```
zmienne programu ──► widok (.shares widoku)
                         └──► rodzic (liczba widoków +1; .shares rodzica bez zmian)
```

- **Widok trzyma rodzica przez liczbę widoków**, a nie przez `.shares`. Menedżer zwalnia blok dopiero wtedy, gdy **oba** liczniki wynoszą 0, więc rodzic nie zniknie, dopóki istnieje choć jeden widok.
- **Rodzic może stracić swoją zmienną, a widoki dalej działają.** Gdy program przestanie używać zmiennej rodzica (np. kończy się funkcja, w której powstał), jego `.shares` spada do 0, ale blok zostaje w pamięci, a widoki pracują na tych samych danych. Pamięć znika dopiero razem z ostatnim widokiem.
- **Widok kończy życie** przez `.release` albo gdy jego `.shares` spadnie do 0. Wtedy opis widoku jest zwalniany, a liczba widoków rodzica maleje o 1.
- **Bloku z aktywnymi widokami nie można zwolnić.** `.release` na takim bloku to błąd: w kompilacji testowej zatrzymanie z komunikatem („blok ma 3 aktywne widoki”), w finalbake zachowanie według `DEFAULT_RANGE_ERROR`. Programista najpierw zwalnia widoki, potem blok.
- **`.update` na bloku z widokami jest dozwolone:** po powiększeniu lub przeniesieniu widoki od razu widzą dane w nowym miejscu, a po zmniejszeniu część widoku może wypaść poza blok i dostęp reaguje zgodnie z `.rangeError`.
- **Widoki nigdy nie tworzą cykli:** widok trzyma rodzica, ale rodzic nie trzyma widoku (tylko liczy, ile ich ma).

---

## 15. Pliki mapowane (`.map`)

```
skan as pointer
skan.map["skan_3d.bin"]                    # plik 50 GB, tylko do odczytu
x = skan.float[1000000]                    # odczyt jak ze zwykłego bloku

tekstura.map["teren_16k.raw", WRITABLE]    # odczyt i zapis
```

`.map` podpina plik z dysku jako blok pamięci (*memory-mapped file*). Nic nie jest wczytywane z góry: dopiero gdy program sięga do konkretnego miejsca, system operacyjny doczytuje z dysku tylko ten kawałek, a dawno nieużywane kawałki sam usuwa z pamięci. Program może więc pracować na pliku większym niż cała pamięć RAM.

Dla kodu programu blok zmapowany wygląda identycznie jak zwykły: te same soczewki, widoki i struktury. Flaga `MAPPED` mówi menedżerowi, co robić inaczej „pod spodem”:

- **zwalnianie:** blok jest odpinany od pliku, a wcześniej wszystkie zmiany są zapisywane na dysk,
- **zmiana rozmiaru:** `.update` najpierw powiększa plik na dysku, a potem podpina go ponownie,
- **wzory pamięci nie są stosowane**, bo nadpisałyby prawdziwe dane z dysku,
- **zapis jest trwały:** zmiana bloku zmienia plik na dysku.

### Zapis tylko na jawne życzenie: `WRITABLE`

Zapis na dysk jest trwały i nieodwracalny, więc musi być świadomą decyzją. **Domyślnie plik mapowany jest tylko do odczytu.** Zapis programista zamawia przy otwieraniu pliku parametrem `WRITABLE`, co ustawia flagę `MAPPED_WRITABLE` (bit 4).

- **Zapis do pliku tylko do odczytu jest zawsze błędem.** Gdy kompilator może to wykryć (widzi `.map` bez `WRITABLE`, a potem zapis), zgłasza błąd kompilacji. Gdy nie może (np. blok przekazany do funkcji), chroni go system operacyjny: strony pliku są podpięte tylko do odczytu, więc próba zapisu zatrzymuje program. To ochrona sprzętowa, więc nic nie kosztuje przy normalnej pracy.
- Tryb `CONTINUE` nie ma tu zastosowania: nie da się „trochę” zapisać do pliku, którego nie wolno zmieniać.
- **`.update` na pliku tylko do odczytu jest niedozwolone**, bo zmiana rozmiaru oznaczałaby zmianę pliku na dysku.

```
tekstura.map["teren_16k.raw", WRITABLE]
kafelek = tekstura.viewPortion[start:rozmiarKafelka]
kafelek.halffloat *= 1.2       # rozjaśnienie jednego kafelka, zapis wprost do pliku
```

Pamięć zajmuje tylko przetwarzany fragment, a reszta pliku zostaje na dysku. W przyszłości ten sam mechanizm może sięgać do plików na innych maszynach (klastry, nieograniczone pola danych).

> Jak to działa w środku: [bemol-wnetrze.md, rozdział 8 (pliki mapowane)](bemol-wnetrze.md#8-pliki-mapowane)

---

## 16. Struktury (`STRUCT`)

**Struktura to zestaw aliasów ze stałymi przesunięciami**, a nie pudełko na dane jak w C. Deklaracja nie przydziela pamięci, tylko mówi kompilatorowi, gdzie leżą pola względem początku struktury.

```
Color as STRUCT { R as unsigned_16, G as unsigned_16, B as unsigned_16, Alpha as unsigned_32 }
```

- **Struktura jest „ciasna”:** pola leżą jedno za drugim, bez pustych bajtów wyrównania. `Color` = 2+2+2+4 = **10 bajtów**.
- **Pola mogą mieć dowolną liczbę bitów** (`bit`, `unsigned_N`, `signed_N`), a kompilator sam obsługuje pola zaczynające się w środku bajtu.
- **Rozmiar całej struktury jest zaokrąglany w górę do pełnego bajtu.** Brakujące bity na końcu to nieużywane wypełnienie. Dzięki temu każdy element tablicy struktur (`ptr.S[n]`) zaczyna się na granicy bajtu i dostęp do niego jest szybki.
- **Nazwa struktury działa jak każdy typ**: w wyrażeniach rozmiaru (`new[100*Color]`) i jako soczewka.
- **Struktura nie jest właścicielem danych.** Blok dalej należy do zmiennej `pointer` i można go czytać innymi strukturami, bajtami czy bitami.
- Przesunięcia są stałe, więc struktura **nic nie kosztuje** w działającym programie.

```
ptr.new[100*Color]
ptr.Color[32].G = 500          # pole G w pikselu nr 32
x = ptr.Color[32].G            # to samo co odczyt 2 bajtów od bajtu 322
```

### Struktury z polami bitowymi

```
Flagi as STRUCT { widoczny as bit, zaznaczony as bit, warstwa as unsigned_6 }   # 8 bitów = 1 bajt
Mix as STRUCT { aktywny as bit, wartosc as unsigned_16 }                         # 17 bitów → 3 bajty (7 bitów wypełnienia)
Raw12 as STRUCT { P0 as unsigned_12, P1 as unsigned_12 }                         # 24 bity = 3 bajty, 2 piksele
```

`Raw12` pokazuje, jak upakować dane bez żadnych przerw: grupuje się elementy tak, żeby razem dały pełne bajty. Dwa piksele 12-bitowe (format surowych zdjęć z aparatów) to dokładnie 3 bajty. Gdy potrzebny jest ciągły strumień bitów bez granic elementów, służą do tego `.bit[]`, `ptr.unsigned_N[n]` i `.value`.

> Jak to działa w środku: [bemol-wnetrze.md, rozdział 4 (struktury z polami bitowymi)](bemol-wnetrze.md#4-struktury-z-polami-bitowymi)

---

## 17. Aliasy (`ALIAS`)

Alias to nazwa nadana stałemu fragmentowi bloku, przez dowolną soczewkę:

```
bitarray as pointer
bitarray.new[2]

CONST LIGHT_BIT as int = 7
ALIAS isLightEnabled as bitarray.bit[LIGHT_BIT]
ALIAS temperatura as czujnik.float[4]

isLightEnabled = true          # to samo co: bitarray.bit[7] = 1
if isLightEnabled then ...
```

- **Pozycja w aliasie jest zawsze stała**: literał albo stała `CONST`. Zmienna jako pozycja jest błędem kompilacji.
- **Alias to tylko nazwa**, podstawiana podczas kompilacji. Nic nie kosztuje i nie zwiększa `.shares`.
- Dla soczewki `.bit` wartości `true` / `false` są tożsame z 1 / 0.
- **Zasięg aliasu** jest taki jak miejsca deklaracji: w funkcji istnieje tylko w niej, poza funkcjami w całym programie.
- Po `.release` bloku alias wskazuje poza blok i zachowuje się zgodnie z `.rangeError`.

Alias nazywa **jeden** fragment konkretnego bloku. Struktura opisuje **zestaw** pól, który można nałożyć na dowolny blok i dowolną pozycję.

---

## 18. Teksty (`text`)

Tekst w BEMOL-u nie jest osobnym, „magicznym” typem, tylko tym, czym wszystko: **blokiem bajtów**, z jednym dodatkiem. Menedżer pamięci pilnuje, gdzie kończy się prawdziwy tekst.

### Pojemność i długość tekstu

Bufor tekstowy ma zawsze dwie wielkości:

- **pojemność**: ile bajtów zarezerwowano,
- **długość tekstu**: ile z nich zajmuje teraz prawdziwy tekst.

```
pojemność 1024:  [a][b][c][?][?][?] ... [?]
długość 3:        ───────
                  tekst    nieużywane
```

Blok tekstowy ma flagę `TEXT` (bit 5). Pojemność zapisana jest w polu długości wpisu, a długość tekstu w polu zależnym od rodzaju wpisu (sekcja 9). Żadnej dodatkowej pamięci, żadnego znaku końca tekstu.

```
t as text
t.new[1024]          # pojemność 1024, długość tekstu 0
t = "abc"            # długość tekstu 3
t.length             # 3    (długość tekstu)
t.size               # 1024 (pojemność, czyli rozmiar bloku)
```

- **`.length` zwraca długość tekstu** (w bajtach) i istnieje **tylko dla tekstów**, bo to chce wiedzieć człowiek pytający o długość napisu,
- **`.size` zwraca pojemność**, czyli rozmiar bloku, jak dla każdego bloku. Osobne `.capacity` nie jest potrzebne,
- `.length` na zwykłym bloku to błąd kompilacji z podpowiedzią „czy chodziło o `.size`?”,
- **odczyt za końcem tekstu** (`t.byte[500]`, gdy tekst ma 3 bajty) jest wyjściem poza zakres i reaguje według `.rangeError`. Nieużywane bajty za tekstem są niedostępne przez przypadek,
- tekst może mieć do 2^64 bajtów; w praktyce ogranicza go pamięć, a przy tekście z pliku mapowanego dysk.

> **Dlaczego bez zera na końcu tekstu?** W C koniec tekstu oznacza bajt o wartości 0. Żeby poznać długość, trzeba przejść cały tekst, a zapomniane albo nadpisane zero sprawia, że program czyta dalej po pamięci. To jedna z najczęstszych przyczyn błędów bezpieczeństwa w historii informatyki. W BEMOL-u długość tekstu jest zapisana we wpisie menedżera, a jej odczyt to jedna operacja.

### Literały tekstowe

```
nazwa as text = "teren_16k.raw"
powitanie as text = "Zażółć gęślą jaźń\n"
```

- kodowanie **UTF-8**: obsługuje polskie znaki i każdy alfabet, a zwykłe litery łacińskie zajmują 1 bajt,
- znaki specjalne: `\n` (nowa linia), `\t` (tabulator), `\"` (cudzysłów), `\\` (ukośnik),
- **literał w kodzie jest tylko do odczytu**, jak stała. Żeby go zmienić, trzeba zrobić kopię: `t = "abc".copy`.

### Bajty i znaki

- `t.byte[n]` daje surowe bajty, jak w każdym bloku,
- `foreach z in t.char do` przechodzi po znakach (polska litera „ż” to 2 bajty, ale jeden znak),
- `t.charCount` zwraca liczbę znaków.

Celowo nie ma `t.char[n]`. Znaki UTF-8 mają różną długość (1–4 bajty), więc dostanie się do 1000. znaku wymaga przejścia przez 999 poprzednich. Taka operacja wyglądałaby na tanią, a jest kosztowna.

### Dopisywanie: `.append`

```
t as text
t.new[16]
t = "abc"
t.append["def"]          # mieści się: kopiowane 3 bajty, długość tekstu 3 → 6
t.append[nazwaPliku]     # nie mieści się: blok rośnie
```

- **gdy dopisywany tekst mieści się w pojemności**, kopiowane są tylko nowe bajty i zwiększana długość tekstu,
- **gdy się nie mieści, blok jest powiększany przez `.update` dokładnie o tyle, ile trzeba**, bez ukrytego zapasu. Powiększenie może przenieść blok, a widoki na tekst nadal działają,
- przy sporadycznym użyciu (ścieżka do pliku, komunikat) koszt jest pomijalny. Kto przetwarza duże teksty, rezerwuje pojemność z góry: `t.new[1000000]`. W kompilacji testowej kompilator podpowiada, gdy `.append` w pętli wielokrotnie powiększa blok.

### Porównywanie: `==`

- **dwa teksty:** `a == b` porównuje **treść**. Najpierw długości (natychmiast), a dopiero przy równych długościach bajty. Tak, jak oczekuje każdy, kto pisze `if nazwa == "obraz.raw" then`,
- **dwa bloki `pointer`:** `a == b` znaczy „ten sam blok” (porównanie numerów wpisów, natychmiastowe). Porównanie treści dużych bloków to funkcja biblioteki, bo jest kosztowne,
- gdy dla tekstów potrzebne jest „ten sam blok”, zapisuje się to jawnie: `a.pointer == b.pointer`.

### Pozostałe operacje

Wyszukiwanie, wycinanie, zamiana liczby na tekst i odwrotnie należą do biblioteki standardowej (sekcja 24).

> Jak to działa w środku: [bemol-wnetrze.md, rozdział 11 (teksty w środku)](bemol-wnetrze.md#11-teksty-w-środku)

---

## 19. Wyjście poza blok: `.rangeError`

Dotyczy **wyłącznie bloków** (zmiennych `pointer` i widoków). Zmienne statyczne nie są sprawdzane (sekcja 5).

| Wartość | Tryb | Działanie |
|---|---|---|
| 0 | `DEFAULT` | zachowanie domyślne, ustawione przez `DEFAULT_RANGE_ERROR` |
| 1 | `CONTINUE` | program działa dalej, zgodnie z zasadami odłamków |
| 2 | `WARNING` | program działa dalej i zgłasza ostrzeżenie (sekcja 20) |
| 3 | `HALT` | program zatrzymuje się |

```
ptr.rangeError = 1                 # dla jednej zmiennej
DEFAULT_RANGE_ERROR = CONTINUE     # domyślnie dla całego programu
```

Standardowo `DEFAULT_RANGE_ERROR = HALT`. Tryb każdego bloku jest zapisany w bitach 8–9 jego wpisu w menedżerze.

---

## 20. Ostrzeżenia i komunikaty błędów

### Ostrzeżenia (`WARNING`)

**Kompilacja testowa:** kompilator dołącza zapisywanie ostrzeżeń do pliku logu obok programu (`nazwa_programu.warnings.log`). **Każde miejsce w kodzie zgłasza ostrzeżenie tylko raz**, a przy kolejnych wystąpieniach rośnie licznik. Na końcu programu w logu pojawia się podsumowanie, np. „linia 128: 999 999 kolejnych wystąpień”. Dzięki temu pętla wychodząca milion razy poza blok nie zaleje logu.

**Finalbake:** ostrzeżenia trafiają wyłącznie do funkcji obsługi zdefiniowanej przez programistę. Bez niej nie trafiają nigdzie.

```
WARNING_HANDLER = mojeOstrzezenia

FUNCTION mojeOstrzezenia(info as pointer)
    ...    # np. pokaż w oknie, zapisz do bazy, wyślij na serwer
mojeOstrzezenia.end
```

Ostrzeżenie zawiera: numer bloku, pozycję dostępu, długość bloku, rodzaj dostępu (odczyt czy zapis) i miejsce w kodzie (plik i linia).

W finalbake bez `WARNING_HANDLER` tryb `WARNING` zachowuje się dokładnie jak `CONTINUE`, więc kompilator może wygenerować dla niego ten sam, najprostszy kod.

### Komunikaty błędów

Wiele kompilatorów zgłasza błędy tak, że nie wiadomo, co je wywołało. W BEMOL-u **każdy błąd mówi co, gdzie, dlaczego i jak naprawić**, a kompilator wypisuje go w dwóch formach z jednego źródła: dla człowieka i dla agenta AI.

**Forma dla człowieka**: ramka, w której każda informacja ma stałe miejsce:

```
*****************************************************************
ERROR: BML-E0412
obraz.bmol
at line 57, column 5
-----------------------------------------------------------------
57 |     obraz.release
   |     ^
-----------------------------------------------------------------
  [ ! ] Zwalniasz blok, na który patrzą widoki
  [ i ] blok „obraz” ma 1 aktywny widok: „kafelek” utworzony w linii 41, kolumnie 15
[ tip ] najpierw zwolnij widok: kafelek.release
_________________________________________________________________
```

| Element | Znaczenie |
|---|---|
| linia `*****` | początek **błędu** (ostrzeżenie zaczyna się linią `=====`) |
| `ERROR: BML-E0412` / `WARNING: BML-W0311` | rodzaj i stały kod |
| nazwa pliku, `at line N, column K` | dokładne miejsce |
| linia kodu z `^` | fragment, którego dotyczy komunikat |
| `[ ! ]` | **co** jest źle, jednym zdaniem |
| `[ i ]` | **dlaczego**: szczegóły, powiązane miejsca, złamana zasada (opcjonalne) |
| `[ tip ]` | **jak naprawić**: gotowy zapis do wpisania (opcjonalne) |
| linia `_____` | koniec komunikatu |

Ostrzeżenie ma tę samą budowę:

```
=================================================================
WARNING: BML-W0311
kanaly.bmol
at line 24, column 10
-----------------------------------------------------------------
24 |     case 5
   |          ^
-----------------------------------------------------------------
  [ ! ] Gałąź case 5 nigdy się nie wykona
  [ i ] wartość 5 obsługuje już case 1 to 10 z linii 20 (pierwsza pasująca gałąź wygrywa)
[ tip ] przenieś case 5 nad case 1 to 10 albo usuń tę gałąź
_________________________________________________________________
```

**Błąd w działającym programie** (np. `HALT` z `.rangeError`, `.release` bloku z widokami) ma tę samą ramkę, tylko bez linii kodu, bo program nie ma już przy sobie źródła: plik, linia, `[ ! ]`, `[ i ]` z liczbami (numer bloku, pozycja, długość) i `[ tip ]`. Program kończy się wtedy kodem 70.

**Forma dla agenta AI** (opcja kompilatora `-diagnostics=json`):

```json
{
  "code": "BML-E0412",
  "severity": "error",
  "message": "release of block with active views",
  "file": "obraz.bmol", "line": 57, "column": 5, "length": 13,
  "related": [
    { "role": "view_created", "file": "obraz.bmol", "line": 41, "column": 15 }
  ],
  "rule": "spec#14",
  "fix": { "insert_before_line": 57, "text": "kafelek.release" }
}
```

**Zasady:**

1. **Stały kod błędu** (`BML-E0412`). Kod nigdy się nie zmienia i ma własną stronę w dokumentacji z przykładami. Agent AI może go wyszukać, a człowiek wkleić w wyszukiwarkę.
2. **Dokładne miejsce:** plik, linia, kolumna i podkreślenie fragmentu, a nie tylko numer linii.
3. **Powiązane miejsca:** gdy przyczyna leży gdzie indziej (widok utworzony wyżej, `CONST` zadeklarowane w innym pliku), komunikat wskazuje także tamto miejsce.
4. **Zasada, która została złamana**, z odnośnikiem do sekcji specyfikacji.
5. **Konkretna propozycja naprawy.** W formie JSON jako dokładny tekst do wstawienia, który agent może zastosować automatycznie.
6. **Jedna przyczyna, jeden błąd.** Gdy jeden błąd pociąga za sobą kolejne, kompilator zgłasza przyczynę, a skutki oznacza jako „następstwo BML-E...” albo pomija. Nie zalewa programisty lawiną komunikatów.
7. **Ten sam format dla błędów w działającym programie.** `HALT` z `.rangeError` wypisuje kod, nazwę zmiennej, pozycję, długość bloku, linię i łańcuch wywołań funkcji. Log ostrzeżeń z kompilacji testowej też ma oba formaty.
8. **Pola formy JSON zawsze po angielsku i stałe**, a komunikat dla człowieka w języku programisty. Pierwszym językiem komunikatów jest angielski (pod niego budowana będzie społeczność), drugim polski.


### Potwierdzanie ostrzeżeń: `@ACCEPT`

Gdy programista uznaje ostrzeżenie za zamierzone, potwierdza to jawnie, **dokładnie przy instrukcji, której dotyczy**:

```
switch kanal
    case 5 @ACCEPT WARNING            # 5 ma osobną obsługę
        ...
    case 1 to 10
        ...
switch.end

dane.byte[5] = licznik @ACCEPT WARNING      # celowo 4 B: zapis całego licznika
```

- **`@ACCEPT` stoi na końcu instrukcji** (w tej samej linii lub części oddzielonej `;`) i dotyczy tylko jej. Nie ma wersji obejmującej blok ani cały plik,
- **musi stać dokładnie tam, gdzie kompilator zgłasza ostrzeżenie**. Akceptacja w innym miejscu jest błędem z podpowiedzią, gdzie ją przenieść. Przy instrukcji przeniesionej na kilka linii stoi na końcu ostatniej,
- **`@ACCEPT WARNING` potwierdza wszystkie ostrzeżenia tej jednej instrukcji**, bez podawania kodów. Zakres jest i tak tylko jedna instrukcja, więc pamiętanie numerów ostrzeżeń byłoby zbędnym balastem,
- **uzasadnienie to zwykły komentarz `#`** w tej samej linii. Opcjonalny, ale zalecany: za rok widać, dlaczego tak zostało,
- **tylko ostrzeżenia, nigdy błędy.** Błąd trzeba naprawić,
- **zbędne potwierdzenie:** gdy ostrzeżenie już nie występuje, kompilator informuje, że `@ACCEPT` można usunąć,
- **przed `-finalbake`** narzędzia pokazują listę ostrzeżeń nierozstrzygniętych i zaakceptowanych: przy każdym zaakceptowanym miejscu kody ostrzeżeń, które w nim występują, i komentarz z uzasadnieniem. Gdy po zmianie kodu ta sama instrukcja zacznie dawać nowe, inne ostrzeżenie, `@ACCEPT WARNING` je przykryje, ale jego kod będzie widoczny na tej liście.

Każda akceptacja jest widoczna dokładnie tam, gdzie zapadła decyzja. Kod z wieloma `@ACCEPT` sam zadaje pytanie „dlaczego?”, i o to chodzi: ostrzeżenie nie znika po cichu, tylko zamienia się w udokumentowaną decyzję. Potwierdzenia są zapisane w kodzie źródłowym, więc nie giną po otwarciu projektu w innym edytorze.

---

## 21. Zestawienie operacji na `pointer`

### Zarządzanie blokiem

| Operacja | Działanie |
|---|---|
| `ptr` | działa jak `ptr.pointer` |
| `ptr.pointer` | zwraca adres bloku |
| `ptr.new[*]` | rejestruje zmienną i przydziela pierwszy blok: `[rozmiar]` lub `[ilość*typ]`. Tylko raz. Nie zeruje bloku |
| `ptr.update[*]` | zmienia rozmiar, zachowując dane; nowe bajty mają nieokreśloną zawartość. Po `.release` przydziela nowy blok |
| `ptr.release` | zwalnia blok, `.size` = 0; zmienna pozostaje zarejestrowana. Niedozwolone przy aktywnych widokach |
| `ptr.clear` | zeruje cały blok (zawsze wykonywane, także tuż przed `.release`) |
| `ptr.fill[wartość]` | wypełnia blok powtarzanym wzorem (sekcja 12) |
| `ptr.map["plik"]` | podpina plik z dysku jako blok pamięci, tylko do odczytu |
| `ptr.map["plik", WRITABLE]` | podpina plik z dysku do odczytu i zapisu |
| `ptr.shares` | zwraca liczbę użyczeń |
| `ptr.size` | zwraca rozmiar bloku w bajtach (0 = brak bloku); dla tekstu pojemność |
| `t.length` | tylko tekst: długość tekstu w bajtach |
| `ptr.rangeError = <tryb>` | zachowanie przy wyjściu poza blok |
| `ptr.memoryPatternDebug = ON/OFF` | wypełnianie nowych bajtów wzorem w kompilacji testowej |
| `ptr.memoryPatternProduction = ON/OFF` | wypełnianie nowych bajtów wzorem w finalbake |

### Odczyt i zapis

| Operacja | Działanie |
|---|---|
| `ptr.value` | cały blok jako jedna liczba (największa soczewka) |
| `ptr.value = <wartość>` | zapisuje wartość od bajtu 0 |
| `ptr.<typ>[n]` | element przesunięty o n × rozmiar typu; odczyt i zapis zawsze w szerokości typu (sekcja 10) |
| `ptr.<typ>.at[n]` | wartość typu od bajtu n (pozycja w bajtach) |
| `ptr.<typ>` | bez indeksu: cały blok jako ciąg elementów (operacje blokowe) |
| `ptr.<typ>.count` | liczba pełnych elementów typu w bloku |
| `ptr.<Struktura>[n].pole` | pole struktury w n-tym elemencie, np. `ptr.Color[32].G` |
| `n = INPUT.read[ptr]` | wypełnia blok kolejnymi bajtami wejścia programu; `n` = liczba przeczytanych bajtów, 0 = koniec danych (sekcja 3) |

### Widoki i kopie

| Operacja | Działanie |
|---|---|
| `ptr.viewPortion[od:ile]` | widok na ciągły fragment, bez kopiowania |
| `ptr.viewRectangle[x, y, w, h, krok]` | widok na prostokąt, bez kopiowania |
| `ptr.copy` | nowy blok z kopią całej zawartości |
| `ptr.copyPortion[od:ile]` | nowy blok z kopią ciągłego fragmentu |
| `ptr.copyRectangle[x, y, w, h, krok]` | nowy blok z kopią prostokąta (wiersze ułożone ciągiem) |

Wszystko, co zaczyna się od `copy`, tworzy nowe dane. Wszystko, co zaczyna się od `view`, pokazuje istniejące.

---

## 22. Kompilator

### Kompilacje cząstkowe

- **Kompilator sam dobiera wielkość cząstek** (najczęściej pojedyncze funkcje i metody), kompiluje je osobno i przechowuje wyniki w ukrytym folderze **`.bemol-cache/`** obok projektu. Folder można w każdej chwili usunąć, a kompilator odbuduje go przy następnym uruchomieniu.
- **Kompilator sam śledzi zależności.** Każda skompilowana cząstka zapamiętuje, z jakich deklaracji korzysta (`STRUCT`, `CONST`, `ALIAS`, `GLOBAL`, inne funkcje). Ponieważ ich wartości są „wpieczone” w kod, zmiana deklaracji (np. nowe pole w `Color`) przekompilowuje wszystkie cząstki, które jej używają, i tylko je. Programista nic nie robi.
- **`-finalbake`** korzysta z cząstek, ale optymalizuje całość od nowa, m.in. wklejając małe funkcje w miejsca wywołań, czego przy osobnej kompilacji nie da się zrobić.

**Cel na przyszłość (nie wymaganie):** podmiana funkcji w działającym programie, jak Live Coding w Unreal Engine. Możliwa tylko dla zmian wewnątrz funkcji, zawsze dla całej grupy zależnych funkcji naraz. Przy zmianie `STRUCT`, `GLOBAL` czy `CONST` dane w pamięci mają już stary układ, więc wymagany byłby restart programu.

### Wymagane optymalizacje

Model pamięci BEMOL-a (uchwyty w menedżerze, licznik `.shares`, kontrola zakresu) ma swój koszt. Żeby język dotrzymał obietnicy szybkości, kompilator musi go ograniczać. Wszystkie te optymalizacje dotyczą **maszynerii kompilatora**, nigdy operacji programisty:

1. **Adres bloku odczytywany raz przed pętlą.** W pętli adres się nie zmienia, więc kompilator odczytuje go z menedżera raz, trzyma w rejestrze procesora i w środku działa na zwykłym adresie, z prędkością C. Adres jest odczytywany ponownie tylko po operacjach, które mogą przenieść blok (`.update`, `.release`).
2. **Usuwanie zbędnych zmian `.shares`.** Licznik zmienia się przy wejściu do bloku programu i wyjściu z niego, nigdy przy samym dostępie do danych. Kompilator usuwa pary +1/−1, które się znoszą, np. gdy funkcja tylko czyta blok i nigdzie go nie przekazuje.
3. **Sprawdzanie zakresu raz przed pętlą.** W pętli od 0 do N kompilator sprawdza przed jej rozpoczęciem, czy cały zakres mieści się w bloku, a w środku pętli nie sprawdza już niczego.

> Jak to działa w środku: [bemol-wnetrze.md, rozdział 9 i 10 (optymalizacje kompilatora i kompilacje cząstkowe)](bemol-wnetrze.md#9-optymalizacje-kompilatora)

---

## 23. Narzędzia

### Zasada: wiedza w kompilatorze

Cała wiedza o programie (podpowiedzi, ostrzeżenia, szerokości, adresy, komunikaty błędów) jest w **kompilatorze** i jest udostępniana przez standardowy protokół dla edytorów (*Language Server Protocol*, LSP). Dzięki temu:

- działa w planowanym środowisku BEMOLIZER,
- działa w każdym popularnym edytorze obsługującym LSP (np. VS Code), bez dodatkowej pracy,
- agenty AI korzystają z tych samych danych w formacie JSON (sekcja 20).

### BEMOLIZER

Planowane środowisko programistyczne BEMOL-a:

- **lista kontrolna ostrzeżeń przed `-finalbake`**: nierozstrzygnięte i zaakceptowane (`@ACCEPT`), z uzasadnieniami,
- **podgląd zawartości bloków** przy debugowaniu,
- **wizualizacja widoków prostokątnych** na danych obrazu,
- przełączanie trybów kompilacji z menu, podgląd logu ostrzeżeń.

### Planowane podpowiedzi

- **soczewka:** pozycja w bajtach i bitach oraz szerokość odczytu, np. przy `ptr.int[5]`: „bajt 20, 4 B”,
- **szerokość literału** po najechaniu kursorem,
- **wyróżnienie szerokości natywnych** (8, 16, 32, 64) i informacja przy nienatywnych,
- **kopia czy widok:** czy operacja tworzy nowe dane (`copy...`), czy tylko pokazuje istniejące (`view...`),
- **`.update`:** informacja, że blok może zostać przeniesiony,
- **koszty w pętlach:** `.new` lub wielokrotne powiększanie przez `.append` wewnątrz pętli.

Celem narzędzi jest pomaganie programiście w podejmowaniu decyzji i pokazywanie potencjalnych niebezpieczeństw w prosty i czytelny sposób.

---

## 24. Język a biblioteka standardowa

> **Do języka trafia to, co odpowiada jednej instrukcji procesora albo wymaga wiedzy kompilatora, żeby działało szybko. Całe algorytmy idą do biblioteki standardowej.**

**W języku:** soczewki, operacje blokowe, operacje bitowe (sekcja 13), liczenie bitów, nasycenie (`saturate`), redukcje, zamiana kolejności bajtów, widoki i kopie.

**W bibliotece standardowej:** mnożenie macierzy, splot (konwolucja), FFT, szyfrowanie (AES), skróty (SHA), arytmetyka wielkich liczb (dodawanie i mnożenie bloków jako liczb), generatory liczb losowych, funkcje aktywacji sieci neuronowych, sortowanie, operacje na tekstach (wyszukiwanie, wycinanie, zamiana liczb na tekst), porównanie treści bloków, `clamp(x, min, max)`.

Powody: algorytmów jest bardzo dużo, zmieniają się z czasem, a najlepsza implementacja zależy od sprzętu (CPU, karta graficzna, specjalne instrukcje procesora, np. dla AES). Biblioteka może z nich korzystać i być wymieniana bez zmiany języka, a sam język zostaje mały i łatwy do nauki.

---

## 25. Obiekty: klasy uproszczone

Klasyczna obiektowość (C++, Java) zawiera mechanizmy, które szkodzą maszynie:

- **dziedziczenie z metodami wirtualnymi**: wywołanie metody wymaga odczytania adresu funkcji z tabeli w czasie działania, więc kompilator nie może wkleić funkcji w miejsce wywołania ani użyć instrukcji wektorowych,
- **obiekty porozrzucane po pamięci**: każdy obiekt to osobny przydział, a tablica obiektów to tablica wskaźników; przejście po milionie obiektów to milion skoków w losowe miejsca pamięci,
- **ukryte operacje**: konstruktory kopiujące, destruktory i przydziały pamięci wywoływane niejawnie przy zwykłym `=`.

Z tych samych powodów silniki gier odchodzą od klasycznych obiektów przy dużej liczbie jednostek (Mass Entity w Unreal Engine, DOTS w Unity).

**W BEMOL-u klasa to struktura z funkcjami.** Uproszczone obiekty są lepsze dla maszyny, a więc i dla programisty:

```
CLASS Czastka
    .pozycja as float
    .predkosc as float

    FUNCTION .Krok(dt as float)
        .pozycja = .pozycja + .predkosc * dt
    Krok.end
Czastka.end

czastki as pointer
czastki.new[100000*Czastka]          # 100 000 cząstek w jednym ciągłym bloku
czastki.Czastka[1000].Krok(0.016)    # metoda na cząstce nr 1000
```

- **Dane klasy to `STRUCT`**: ciasny układ pól, stały rozmiar, może być soczewką.
- **Metody to zwykłe funkcje** z ukrytym `this`, rozstrzygane podczas kompilacji. Zero kosztu w działającym programie.
- **Bez dziedziczenia i metod wirtualnych.** Zamiast dziedziczenia **kompozycja**: struktura zawiera inną strukturę jako pole. Gdy potrzebne są różne zachowania, pole typu i zwykły warunek `if`, jawny i przewidywalny.
- **Konstruktor to zwykła funkcja inicjalizująca**, wywoływana jawnie, bez niejawnych kopii.
- **`PRIVATE`** ukrywa pola i metody; sprawdzane tylko podczas kompilacji, więc nic nie kosztuje.

### Pamięć obiektów: bez osobnego menedżera

Obiekt to tylko dane w pamięci, więc **wszystko obsługuje istniejący menedżer bloków**, bez nowych mechanizmów:

- **obiekt jako zmienna** (lokalna lub `GLOBAL`) leży na stosie jak każda struktura. Kompilator zna jego pola, więc pola typu `pointer` liczą się do `.shares` jak zwykłe zmienne,
- **obiekty w bloku** (`ptr.new[100000*Czastka]`) to surowe dane bloku, a ich pola wskaźnikowe są zwykłymi liczbami, zgodnie z regułą z sekcji 7.

Dzięki temu obiekty nie tworzą cykli, słabe wskaźniki (`WEAK`) nie są potrzebne, a tablica 100 000 cząstek to jeden ciągły blok, który `for.parallel` i instrukcje wektorowe przetwarzają z pełną prędkością.

### Notacja klas

Kropka łączy właściciela z tym, co do niego należy. Pełna nazwa jest zawsze poprawna, a kropka na początku to jej skrót, oznaczający „ta klasa” albo „ten obiekt”:

| Gdzie | Pełna forma | Skrót |
|---|---|---|
| deklaracja pola w klasie | `Klasa.zmienna as int` | `.zmienna as int` |
| deklaracja metody w klasie | `FUNCTION Klasa.Odczytaj(): int` | `FUNCTION .Odczytaj(): int` |
| pole obiektu wewnątrz metody | `this.zmienna = 1` | `.zmienna = 1` |

```
CLASS Licznik
    .wartosc as int
    FUNCTION .Zwieksz()              # deklaracja
Licznik.end

FUNCTION Licznik.Zwieksz()           # definicja poza klasą, pełna nazwa
    .wartosc = .wartosc + 1                # pole tego obiektu (to samo co this.wartosc)
Zwieksz.end
```

- **Wewnątrz metody** `.pole` i `this.pole` oznaczają pole obiektu, na którym działa metoda. Zmienna bez kropki to zmienna lokalna metody, więc od razu widać, co jest polem.
- **Metody można definiować poza klasą** z pełną nazwą (`FUNCTION Klasa.Metoda`), w dowolnym miejscu pliku. Przy dużych klasach deklaracja klasy staje się czytelnym „spisem treści”.
- **Kropka na początku poza klasą to błąd kompilacji**, bo nie ma właściciela, do którego mogłaby się odnosić.
- `this` piszemy małymi literami, bo to odwołanie, używane jak zmienna, a nie słowo budujące strukturę programu.
- **Konstruktor:** wstępna propozycja: parametry należą do konstruktora (zwykłej funkcji inicjalizującej), a sama deklaracja klasy jest bez parametrów (`CLASS Klasa`). Szczegóły do ustalenia.

---

## 26. Zalecany styl

Kompilator wymusza tylko wielkie litery w słowach kluczowych. Nazwy programisty są jego wyborem. Poniższe zalecenia ułatwiają czytanie cudzego kodu, ale **nie są regułami języka**:

- **stałe `CONST` i wartości `ENUM` wielkimi literami** (`ROZMIAR`, `GORACO`), żeby od razu było widać, że to stałe,
- **zmienne i funkcje** z wielką literą na początku kolejnych słów (`isLightEnabled`, `rozjasnijObraz`),
- **struktury, klasy i wyliczenia z wielkiej litery** (`Color`, `Czastka`, `Stan`),
- **deklaracje globalne na górze pliku**, program główny pod nimi, funkcje na dole (sekcja 3),
- **`@ANYTHING_ELSE` na końcu listy wartości** w `case` (`case 1, 7, 19, @ANYTHING_ELSE`): tam oko go szuka. Inna pozycja jest dozwolona i działa tak samo.

W przyszłości BEMOLIZER może mieć opcjonalne narzędzie do ujednolicania stylu w projekcie, uruchamiane świadomie przez zespół, który tego chce.

---

## 27. Przykładowy program

```
GLOBAL obraz as pointer
GLOBAL flagi as pointer

CONST SZER as int = 1920
CONST WYS as int = 1080
CONST LIGHT_BIT as int = 7

Color as STRUCT { R as unsigned_16, G as unsigned_16, B as unsigned_16, Alpha as unsigned_32 }

ALIAS isLightEnabled as flagi.bit[LIGHT_BIT]

MAIN BEGIN
    size as longint
    B as byte
    d as doublefloat = 3.14

    obraz.new[SZER*WYS*Color]         # 20 736 000 bajtów, zawartość nieokreślona
    obraz.clear                       # jawne zerowanie
    size = obraz.size

    obraz.Color[32].G = 500           # pole G w pikselu nr 32 (2 bajty)
    B = obraz.byte[320]               # pierwszy bajt piksela nr 32
    obraz.doublefloat.at[1009] = d    # 8 bajtów od bajtu 1009

    # widok na kafelek 64 × 64 od piksela (100, 50), bez kopiowania
    kafelek as pointer
    kafelek = obraz.viewRectangle[100*Color, 50, 64*Color, 64, SZER*Color]
    kafelek.Color.fill[obraz.Color[0]]

    foreach px in kafelek.Color do    # pętla po pikselach widoku
        px.Alpha = 0
    foreach.end

    # kopia tego samego obszaru do nowego bloku
    miniatura as pointer
    miniatura = obraz.copyRectangle[100*Color, 50, 64*Color, 64, SZER*Color]

    kafelek.release                   # najpierw widok...
    flagi.new[2]
    isLightEnabled = true

    nazwa as text = "teren_16k.raw"
    jestRaw as bit = 0
    if nazwa == "teren_16k.raw" then jestRaw = 1; if.end    # porównanie treści tekstów

    obraz.byte xor= &FFh              # każdy bajt odwrócony
    obraz.byte = saturate(obraz.byte + 20)   # rozjaśnienie bez „przekręcania” jasnych bajtów

    if BUILD_MODE == TEST then
        size = potega(2, 10)
    if.end

    obraz.release                     # ...potem blok (nie ma już widoków)
    obraz.update[100*float]           # nowy blok 400 bajtów, zawartość nieokreślona
    obraz.float = 1                   # wypełnienie wszystkich floatów
    obraz.float *= 2                  # operacja blokowa
MAIN END

FUNCTION potega(base as float, times as int): float
    temp as float = 1
    for i as int = 1 to times do
        temp = temp * base
    for.end
    return temp
potega.end
```

---

## 28. Otwarte pytania

- [ ] **Klasy:** składnia konstruktora i jego parametrów, szczegóły `PRIVATE`, kompozycja struktur w praktyce (sekcja 25).
- [ ] **Katalog kodów błędów:** numeracja `BML-E...` (i ostrzeżeń `BML-W...`) oraz strony dokumentacji dla każdego kodu.
- [ ] **Praca równoległa:** `for.parallel`, `split.chunk`, `split.cores`, tryby widoków (`read` / `write`).
- [ ] **Nazwy operacji wbudowanych:** liczenie bitów, redukcje (suma, min, max, iloczyn skalarny), zamiana kolejności bajtów.
- [ ] **Podmiana funkcji w działającym programie** (cel na przyszłość, sekcja 22).
- [ ] **Pliki:** odczyt i zapis zwykłych plików (poza `.map`).
- [ ] **Programy z wielu plików:** dołączanie funkcji, struktur i stałych z innych plików `.bmol`.
- [ ] **Wyjście z kilku zagnieżdżonych pętli naraz.**
- [ ] **Funkcje biblioteki tekstowej:** wyszukiwanie, wycinanie, zamiana liczb na tekst i odwrotnie, porównanie treści bloków.
- [ ] **Środowisko programistyczne (BEMOLIZER):** szczegóły interfejsu (sekcja 23).
- [ ] **`@ACCEPT RUNTIME_ERROR`**: przyjęcie błędu w działającym programie dla jednej instrukcji, ze wszystkimi jego skutkami (np. `dane.byte[i] = x @ACCEPT RUNTIME_ERROR`: zapis poza blok przepada w odłamkach, program idzie dalej, choć blok ma `.rangeError = HALT`). Działa jak `.rangeError = CONTINUE`, ale tylko dla tej jednej instrukcji. Nazwa sama wyklucza błędy kompilacji. Na start tylko wyjście poza blok (E0100), bo ma już określone zachowanie; każdy kolejny błąd wymaga osobnej decyzji, co znaczy „idź dalej” (np. `.release` bloku z widokami, koniec danych w `keyInput`, krok 0 w `for`).
- [ ] **Blokowanie bloku w pamięci fizycznej** (flaga bloku na wzór `VirtualLock` / `mlock`): przydzielona pamięć może zostać przeniesiona przez system do pliku wymiany; dla zadań czasu rzeczywistego (np. dźwięk na żywo) potrzebna byłaby gwarancja, że blok zawsze zostaje w pamięci RAM.
