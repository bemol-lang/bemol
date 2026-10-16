# BEMOL ♭ — specyfikacja języka

> **BEMOL**: *Boundless Efficient Machine-Oriented Language*
> Repozytorium: `github.com/bemol-lang/bemol` · rozszerzenie plików: `.bmol`
> Status: **szkic roboczy** · ostatnia aktualizacja: 2026-10-16

BEMOL to kompilowany język do szybkiego przetwarzania dużych bloków danych. Daje dostęp do pamięci z precyzją asemblera (każdy bajt, każdy bit), ale z czytelną składnią i automatycznym zarządzaniem pamięcią.

**Dlaczego „bemol”?** Bemol (♭) w muzyce obniża dźwięk. C# poszło „w górę”, ku wysokiemu poziomowi abstrakcji. BEMOL schodzi „w dół”, bliżej sprzętu, do bitów i bajtów.

---

## Spis treści

1. [Filozofia](#1-filozofia)
2. [Tryby kompilacji](#2-tryby-kompilacji)
3. [Składnia ogólna](#3-składnia-ogólna)
4. [Typy, rozmiary i arytmetyka](#4-typy-rozmiary-i-arytmetyka)
5. [Literały](#5-literały)
6. [Typ `pointer`](#6-typ-pointer)
7. [Cykl życia bloku](#7-cykl-życia-bloku)
8. [Menedżer pamięci](#8-menedżer-pamięci)
9. [Soczewki: pozycja i szerokość](#9-soczewki-pozycja-i-szerokość)
10. [Odłamki: niepełne elementy](#10-odłamki-niepełne-elementy)
11. [Operacje blokowe](#11-operacje-blokowe)
12. [Operacje bitowe i inne operacje wbudowane](#12-operacje-bitowe-i-inne-operacje-wbudowane)
13. [Widoki i kopie fragmentów](#13-widoki-i-kopie-fragmentów)
14. [Pliki mapowane (`.map`)](#14-pliki-mapowane-map)
15. [Struktury (`STRUCT`)](#15-struktury-struct)
16. [Aliasy (`ALIAS`)](#16-aliasy-alias)
17. [Wyjście poza blok: `.rangeError`](#17-wyjście-poza-blok-rangeerror)
18. [Ostrzeżenia (`WARNING`)](#18-ostrzeżenia-warning)
19. [Zestawienie operacji na `pointer`](#19-zestawienie-operacji-na-pointer)
20. [Kompilator](#20-kompilator)
21. [Język a biblioteka standardowa](#21-język-a-biblioteka-standardowa)
22. [Obiekty (plany)](#22-obiekty-plany)
23. [Przykładowy program](#23-przykładowy-program)
24. [Otwarte pytania](#24-otwarte-pytania)

---

## 1. Filozofia

**Wszystko jest blokiem pamięci.** Blok sam w sobie nie ma typu. Typ to **soczewka**, przez którą patrzymy na fragment bloku. Ten sam blok można w jednym programie czytać bajtami, liczbami, strukturami czy bitami.

**Każda operacja działa w ramach soczewki.** Przesunięcia bitów, operacje logiczne, arytmetyka, wypełnianie: zawsze dotyczą elementu, który wyznacza soczewka. `.byte` to każdy bajt osobno, `.value` to cały blok jako jedna liczba.

**Jedna notacja.** Wszystkie operacje na zmiennej zapisuje się po kropce: `nazwa.operacja`.

**Czytelnie dla człowieka, szybko dla maszyny.** Nazwy mówią wprost, co robią: wszystko, co kopiuje dane, zaczyna się od `copy`, a wszystko, co tylko pokazuje dane bez kopiowania, od `view`.

**Programista wie, co robi.** Programista BEMOL-a zna sposób zapisu danych w komputerze (wie, że 300 nie mieści się w bajcie) i ponosi za niego odpowiedzialność. Język mu niczego nie zabrania.

**Kompilator wykonuje to, co programista napisał.** Kompilator optymalizuje tylko własną maszynerię (odczyt adresów, liczniki, kontrolę zakresu) i sposób wykonania (rejestry, instrukcje wektorowe, wyliczanie stałych), **nigdy nie pomija operacji programisty**. Jeśli programista napisał `.clear` tuż przed `.release`, blok zostanie wyzerowany.

**Co ma kosztować zero, musi być znane podczas kompilacji.** Rozmiary typów, stałe `CONST`, aliasy i struktury są ustalone przed uruchomieniem programu i kompilator po prostu je podstawia. Elastyczność dają zmienne, indeksy i widoki.

**Nic kosztownego nie dzieje się bez wiedzy programisty.** Kontrole i pomoce (wzory pamięci, ostrzeżenia, `HALT`) programista włącza świadomie, a w finalnym programie może je wyłączyć tam, gdzie liczy się każdy cykl.

**Kolejność bajtów: little-endian.** Bajt 0 jest najmniej znaczący. Blok czytamy jak zapis binarny, „od prawej do lewej”. To naturalny porządek procesorów x86 i ARM.

**Indeksowanie od zera.**

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
if BUILD_MODE = TEST then
    wypiszStanPamieci()
if.end
```

`BUILD_MODE` ma wartość `TEST` lub `FINALBAKE` i jest znana podczas kompilacji. Kod w gałęzi, która w danym trybie nigdy się nie wykona, nie jest dołączany do programu (to nie łamie zasady z sekcji 1: programista sam napisał warunek, który mówi, kiedy kod ma działać).

---

## 3. Składnia ogólna

### Wielkość liter

Język rozróżnia wielkość liter.

- **Słowa kluczowe budujące strukturę programu lub decydujące o życiu zmiennych piszemy WIELKIMI literami** (wymagane): `MAIN`, `BEGIN`, `END`, `CLASS`, `FUNCTION`, `STRUCT`, `GLOBAL`, `PERSISTENT`, `CONST`, `ALIAS`, `PRIVATE`.
- **Słowa przepływu sterowania, operatory, funkcje wbudowane i łączniki piszemy małymi literami:** `for`, `to`, `do`, `if`, `then`, `as`, `return`, `this`, `and`, `or`, `xor`, `not`, `shl`, `shr`, `rol`, `ror`, `saturate`.
- **Wieloczłonowe nazwy wbudowane w język** piszemy z wielką literą na początku kolejnych słów: `rangeError`, `copyPortion`, `viewRectangle`.
- **Nazwy zmiennych, funkcji i klas programisty są dowolne.**

### Zamykanie bloków

Każdy blok zamyka się swoją nazwą z przyrostkiem `.end`:

```
for i = 1 to 10 do
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

**Wyjątek:** program główny ma wyróżnione granice `MAIN BEGIN` / `MAIN END`, żeby od razu rzucały się w oczy.

### Układ pliku

`GLOBAL`, `CONST`, `STRUCT`, `ALIAS`, `CLASS` i `FUNCTION` mogą stać **w dowolnym miejscu pliku, poza MAIN i poza funkcjami**. Kompilator najpierw zbiera wszystkie deklaracje z całego pliku, więc kolejność nie ma znaczenia. Funkcje mogą stać pod programem głównym.

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

### Funkcje

```
FUNCTION potega(base as float, times as int): float
    temp as float = 1
    for i = 1 to times do
        temp = temp * base
    for.end
    return temp
potega.end
```

Wartość zwraca się zwykłym `return`. Metody klasy zapisuje się z kropką na początku nazwy (`FUNCTION .multiply(...)`).

### Stos i sterta

- **Zmienne statyczne, o stałym rozmiarze** (`int`, `float`, `byte`...), trafiają na **stos**. Procesor przydziela i zwalnia dla nich miejsce jedną instrukcją przy wejściu do funkcji i wyjściu z niej, więc kosztują praktycznie zero. Każde wywołanie funkcji, także rekurencyjne, ma własne kopie.
- **Zmienne `pointer`** mają blok na **stercie** i wpis w menedżerze pamięci (sekcja 8).

---

## 4. Typy, rozmiary i arytmetyka

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
| struktura | `STRUCT` | suma pól, zaokrąglona do pełnego bajtu (sekcja 15) |

Nazwy `byte`, `shortint`, `int` i `longint` to wygodne nazwy najczęstszych przypadków ogólnej reguły `unsigned_N` / `signed_N`. Poza tym język nie ma synonimów typów (np. nie ma `integer` obok `int`), żeby kod w jednym projekcie wyglądał jednolicie.

### Typy o dowolnej liczbie bitów: `unsigned_N` i `signed_N`

Dla dowolnego **N od 1 do 64**:

```
zmienna as unsigned_14       # wartości 0–16383
probka as signed_24          # dźwięk 24-bitowy: -8 388 608 – 8 388 607
```

- **jako zmienna**: zajmuje w pamięci tyle pełnych bajtów, ile potrzeba (`unsigned_14` zajmuje 2 bajty, `signed_24` 3 bajty), ale przyjmuje tylko wartości ze swojego zakresu i zawija się na N bitach,
- **w strukturze**: zajmuje dokładnie N bitów (sekcja 15),
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

### Arytmetyka zmiennych statycznych

**Obliczenie odbywa się w typie zmiennej docelowej.** Składniki są najpierw rozszerzane do jej typu:

```
suma as int
suma = ptr.byte[5] + ptr.byte[6]     # 200 + 200 = 400, mieści się w int
```

Gdy nie ma zmiennej docelowej (warunek, porównanie), obliczenie odbywa się w najszerszym typie składników.

**Przepełnienie nie jest sprawdzane: wartość się zawija i zostaje tyle, ile się mieści.** To zachowanie zdefiniowane i przewidywalne, a nie błąd:

```
maly as byte
maly = 200 + 200              # 400 → zostaje 144

duzy as int
duzy = 2147483647 + 1         # → -2147483648
```

Programista zna pojemność swoich zmiennych, więc świadome przepełnienie jest jego decyzją. Brak sprawdzania oznacza zero kosztu przy każdym działaniu. Dla typów zmiennoprzecinkowych przepełnienie daje nieskończoność, zgodnie ze standardem procesora.

**`.rangeError` nie dotyczy zmiennych statycznych**, tylko bloków (sekcja 17).

### Nasycenie: `saturate( )`

Gdy programista nie chce zawijania, może jawnie użyć `saturate( )`. Zamiast „przekręcić” wartość na drugą stronę, nasycenie zatrzymuje ją na **suficie** albo **podłodze** zakresu. **`saturate` nasyca w granicach soczewki** (albo typu zmiennej docelowej): soczewka wyznacza pozycję i zakres wartości, a `saturate` nie pozwala z tego zakresu wyjść.

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

### Zamiana float na typ całkowity

Brana jest **część całkowita, ułamek jest odrzucany** (obcinanie w stronę zera):

```
wynik as int
wynik = 3.7       # 3
wynik = -3.7      # -3
```

Gdy część całkowita jest za duża dla typu, zostaje tyle, ile się mieści.

---

## 5. Literały

**Literał** to wartość zapisana wprost w kodzie. Jego szerokość jest zawsze znana podczas kompilacji.

**Szerokość literału to liczba cyfr razy kwant jego systemu liczbowego:**

| System | Zapis | Kwant | Przykład | Szerokość |
|---|---|---|---|---|
| binarny | `&...b` | 1 bit na cyfrę | `&101b` | 3 bity |
| szesnastkowy | `&...h` | 4 bity na cyfrę | `&FF0ACh` | 20 bitów |
| dziesiętny | zwykła liczba | pełne bajty | `5` | 1 bajt |

- **Zera wiodące się liczą**, bo decyduje zapis, a nie wartość: `&0Fh` to 8 bitów, `&00FFh` to 16 bitów.
- **Literał szesnastkowy i binarny zmienia dokładnie tyle bitów, ile ma zapis**, a nie do pełnego bajtu.
- Literał jest zapisywany od wskazanej pozycji w porządku little-endian: najmniej znacząca część trafia na najniższą pozycję. `ptr.byte[0] = &FF00h` daje bajt 0 = `00`, bajt 1 = `FF`.

> **Kolejność bajtów w przykładach:** w całej specyfikacji zawartość pamięci pokazywana jest **w kolejności adresów, od bajtu 0**. Liczba `&0100h` (256) leży więc w pamięci jako `00 01`: bajt 0 = `00` (mniej znaczący), bajt 1 = `01`. Czytając tę samą liczbę jak zapis binarny, od prawej do lewej, widzimy `01 00`. Obie formy opisują te same dane.

> ⚠️ **Literały dziesiętne mają szerokość zależną od wartości.**
> Z soczewką przyjmują szerokość soczewki (sekcja 9). **Bez soczewki i bez zmiennej** (np. w `.fill` czy `.value =`) zajmują **tyle pełnych bajtów, ile potrzeba dla ich wartości**:
>
> | Literał | Szerokość |
> |---|---|
> | `5`, `255` | 1 bajt |
> | `256`, `300` | 2 bajty |
> | `70000` | 3 bajty |
> | `-1` | 1 bajt (`FF`, zapis ze znakiem) |
> | `-200` | 2 bajty |
> | `1.5` (z ułamkiem) | `doublefloat`, 8 bajtów |
>
> Dlatego `ptr.fill[255]` powtarza wzór 1-bajtowy (bajty od adresu 0: `FF FF ...`), a `ptr.fill[256]` wzór 2-bajtowy (bajty od adresu 0: `00 01 00 01 ...`). Programista musi to wiedzieć. Środowisko programistyczne może pokazywać szerokość literału po najechaniu na niego kursorem.

---

## 6. Typ `pointer`

`pointer` to zmienna wskazująca na blok pamięci przydzielany dynamicznie. Daje dostęp do każdego bajtu i bitu bloku i jest objęta automatycznym zarządzaniem pamięcią.

```
ptr as pointer
GLOBAL ptr as pointer
```

Zadeklarowana zmienna nie ma jeszcze bloku: `ptr.length` zwraca 0.

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

## 7. Cykl życia bloku

### `.new` — rejestracja

**Rejestruje zmienną w menedżerze pamięci** i przydziela pierwszy blok. Można jej użyć **tylko raz w życiu zmiennej**. Rozmiar podaje się w bajtach lub jako `ilość*typ`.

**`.new` nie zeruje bloku.** Zawartość nowego bloku jest nieokreślona (chyba że włączono wzór pamięci, patrz niżej).

```
ptr.new[1024]
ptr.new[100*int]
ptr.clear                  # jawne zerowanie, gdy jest potrzebne
```

### `.update` — zmiana rozmiaru

Zmienia rozmiar bloku, **zachowując istniejące dane**. **Nowo dodane bajty nie są zerowane**: ich zawartość jest nieokreślona. Po `.release` przydziela nowy blok o nieokreślonej zawartości.

Powód: przy bardzo dużych blokach zerowanie to kosztowna operacja, często zbędna, bo programista i tak zaraz wypełni blok własnymi danymi. Kto potrzebuje zer, mówi to jawnie:

```
stary as longint = ptr.length
ptr.update[2048]
ptr.viewPortion[stary:ptr.length-stary].clear    # zeruje tylko nowo dodaną część
```

### `.release` — zwolnienie pamięci

Zwalnia blok i ustawia `.length` na 0. **Rejestracja zmiennej przeżywa `.release`**: inna część programu, która trzyma tę zmienną, nie dostaje wskaźnika donikąd, tylko widzi `.length = 0`, a odczyt zachowuje się zgodnie z `.rangeError`.

**Bloku, na który patrzą widoki, nie można zwolnić** (sekcja 13). Najpierw trzeba zwolnić widoki.

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

**Działanie:** przy `.new` menedżer odczytuje ustawienia domyślne programu i zapisuje je we flagach wpisu (bity 6 i 7, sekcja 8). Ustawienie lokalne nadpisuje domyślne:

- ustawione **przed `.new`**: kompilator je zapamiętuje i stosuje przy rejestracji,
- ustawione **po `.new`**: działa przy kolejnym `.update`.

**Bajt wzoru jest jeden dla całego programu.** We flagach wpisu jest miejsce tylko na włączone/wyłączone, więc pojedyncza zmienna może jedynie włączyć lub wyłączyć wypełnianie.

Wzory nigdy nie są stosowane do plików mapowanych (sekcja 14), bo nadpisałyby dane z dysku.

### Zmienne `pointer` w funkcjach: `PERSISTENT`

**Zwykła zmienna** dostaje nowy wpis w menedżerze przy każdym wywołaniu funkcji.

**Zmienna `PERSISTENT`** ma w menedżerze zarezerwowany wpis, gotowy przy każdym wywołaniu funkcji. Oszczędza to koszt rejestracji w funkcjach wywoływanych bardzo często. **Adres i zawartość bloku nie są gwarantowane** między wywołaniami: trwałe jest miejsce w menedżerze, nie dane. Nazwa nawiązuje do *persistent level* w Unreal Engine: stale obecne jest miejsce, a jego zawartość się zmienia.

```
FUNCTION przetwarzaj(): void
    everyTimeNew as pointer
    PERSISTENT onceAndFast as pointer
przetwarzaj.end
```

**Na końcu funkcji sprawdzane jest `.shares` bloku `PERSISTENT`:**

- **0**: blok był używany tylko w funkcji, wpis jest czyszczony i czeka na kolejne wywołanie,
- **większe od 0**: blok „uciekł” z funkcji (zwrócony, przypisany do zmiennej globalnej). Odłącza się od trybu `PERSISTENT` i staje zwykłym blokiem nowego właściciela, a funkcja dostanie nowy wpis przy następnym wywołaniu.

**Rekurencja:** gdy wpis `PERSISTENT` jest zajęty przez trwające wywołanie, kolejne wywołanie dostaje zwykły blok. `PERSISTENT` to optymalizacja, więc w trudnym przypadku z niej rezygnuje, a program działa poprawnie.

---

## 8. Menedżer pamięci

### Tablica przydziałów

Menedżer pamięci to **tablica dynamiczna**, w której każdy wiersz opisuje jeden przydział. **Numer wiersza jest identyfikatorem bloku**: zmienna `pointer` przechowuje tylko ten numer (4 bajty). Dostęp do wpisu jest natychmiastowy (początek tablicy + numer × 32). Numery po zwolnionych przydziałach są ponownie wykorzystywane dzięki liście wolnych miejsc.

| Pole | Rozmiar | Opis |
|---|---|---|
| adres | 8 B | położenie bloku w pamięci (dla widoku: numer opisu w tablicy widoków) |
| długość | 8 B | rozmiar bloku w bajtach (do 2^64 B ≈ 16 milionów TB) |
| shares | 4 B | liczba użyczeń |
| flagi | 4 B (32 bity) | cechy serwisowe bloku, tabela poniżej |
| zarezerwowane | 4 B | do wykorzystania w przyszłości |
| liczba widoków | 2 B | ile widoków patrzy na ten blok (do 65 535) |
| zarezerwowane | 2 B | do wykorzystania w przyszłości |

**Wpis ma 32 bajty**, w tym 6 bajtów zarezerwowanych na przyszłość (np. numer maszyny w klastrze, na której leży blok). To potęga dwójki, więc procesor znajduje wpis jednym przesunięciem bitowym, a w jednej linii pamięci podręcznej (64 B) mieszczą się dokładnie dwa wpisy. Milion jednoczesnych bloków to 32 MB.

Gdy `.update` musi przenieść blok w inne miejsce, zmienia się tylko adres we wpisie. Wszystkie zmienne i widoki wskazujące ten przydział od razu widzą nowy adres.

**Wolny wpis** rozpoznaje się po `.shares` = 0 **i** liczbie widoków = 0. Zmienna po `.release` ma `.shares` > 0 (nadal ktoś ją trzyma) i `.length` = 0.

### Flagi wpisu (bity serwisowe)

| Bit | Flaga | Znaczenie |
|---|---|---|
| 0 | `GLOBAL` | blok należy do zmiennej globalnej |
| 1 | `PERSISTENT` | zarezerwowany wpis zmiennej `PERSISTENT` w funkcji |
| 2 | `VIEW` | wpis jest widokiem na inny blok (sekcja 13) |
| 3 | `MAPPED` | blok to plik podpięty przez `.map` (sekcja 14) |
| 4 | `MAPPED_WRITABLE` | plik mapowany otwarty do zapisu (ma sens tylko razem z `MAPPED`) |
| 5 | — | zarezerwowany na przyszłe cechy bloku |
| 6 | `DEBUG_MEMORY_PATTERN` | wypełnianie nowych bajtów wzorem w kompilacji testowej |
| 7 | `PRODUCTION_MEMORY_PATTERN` | wypełnianie nowych bajtów wzorem w finalbake |
| 8 | `rangeError`, bit młodszy | tryb wyjścia poza blok (sekcja 17) |
| 9 | `rangeError`, bit starszy | |
| 10–31 | — | wolne |

**Tryb `rangeError`** zapisany jest na dwóch bitach: wartość = bit 9 × 2 + bit 8, czyli 0 = `DEFAULT`, 1 = `CONTINUE`, 2 = `WARNING`, 3 = `HALT`. Wartość 0 oznacza „sprawdź ustawienie domyślne programu” (`DEFAULT_RANGE_ERROR`).

### Liczba użyczeń `.shares`

- gdy element programu (funkcja, pętla, program główny) zaczyna używać bloku, `.shares` rośnie o 1,
- przypisanie `ptr2 = ptr` zwiększa `.shares` o 1,
- gdy element programu się kończy, `.shares` maleje o 1,
- widoki **nie** zmieniają `.shares` rodzica, tylko jego **liczbę widoków** (sekcja 13),
- **pamięć jest zwalniana automatycznie, gdy `.shares` = 0 i liczba widoków = 0.**

Każdy licznik mówi jedną rzecz: `.shares` to liczba zmiennych trzymających blok, a liczba widoków to liczba widoków na niego patrzących.

Zmienna `GLOBAL` należy do programu głównego, więc jej `.shares` nie spadnie do 0 przed końcem programu. Pamięć można zwolnić wcześniej ręcznie, przez `.release`.

---

## 9. Soczewki: pozycja i szerokość

Każdy dostęp do bloku przez soczewkę (`ptr.<typ>[n]`) rozstrzyga dwie rzeczy: **gdzie** zaczynamy i **ile** czytamy lub zapisujemy.

### Pozycja: wyznacza soczewka

Indeks to przesunięcie **w jednostkach typu soczewki**, liczone od zera. Każdy typ liczy w swoich jednostkach, bez wyjątków:

```
ptr.Color[32]     # 32 × Color (10 B) = bajt 320
ptr.int[4]        # 4 × int (4 B)     = bajt 16
ptr.byte[7]       # 7 × byte (1 B)    = bajt 7
ptr.bit[1]        # 1 × bit           = bit 1
```

### Szerokość: wyznacza druga strona

Dotyczy przypisań, porównań i działań. „Druga strona” to strona przeciwna soczewce (soczewka może stać po lewej lub po prawej).

> **Szerokość wyznacza kolejno:** typ zmiennej lub stałej `CONST` → długość bitowa literału szesnastkowego/binarnego → soczewka, która rzutuje literał dziesiętny na swój typ.

1. **Druga strona ma znany typ** (zmienna, stała `CONST`): decyduje jej typ.
2. **Druga strona ma znaną tylko długość** (literał szesnastkowy lub binarny): liczba bitów wynika z długości literału.
3. **Druga strona nie mówi nic o szerokości** (literał dziesiętny, np. `0`, `5`, `255`, albo inna soczewka): decyduje typ soczewki.

```
d as doublefloat
licznik as int

d = ptr.byte[1009]                 # 1: odczyt 8 bajtów od bajtu 1009
ptr.byte[1009] = d                 # 1: zapis 8 bajtów (1009–1016)
if ptr.byte[5] > licznik then      # 1: odczyt 4 bajtów od bajtu 5
ptr.byte[7] = &FF0ACh              # 2: zapis 20 bitów od bajtu 7
ptr.byte[7] = &0111001b            # 2: zapis 7 bitów, ósmy bit bez zmian
ptr.byte[i] = 0                    # 3: zapis 1 bajtu
if ptr.int[78] > 5 then            # 3: odczyt 4 bajtów od bajtu 312
suma = ptr.byte[5] + ptr.byte[6]   # 3: każda soczewka po 1 bajcie
wynik.Color[0] = obraz.Color[17]   # 3: przeniesienie całego piksela (10 B)
```

Soczewka służy więc do **ustawienia pozycji**, a druga strona mówi, **ile miejsca zajmują dane**. Dzięki temu można zapisać lub odczytać wartość dowolnego typu od dowolnego miejsca: `ptr.byte[1009] = d`.

**Ostrzeżenie kompilatora:** gdy druga strona jest szersza niż soczewka (np. `int` z soczewką `.byte`), kompilator zgłasza ostrzeżenie, np. „zapis 4 bajtów przez soczewkę 1-bajtową”. Kod działa zgodnie z regułą 1, a ostrzeżenie pomaga wychwycić przypadkowe nadpisanie sąsiednich bajtów. Można je wyłączyć.

---

## 10. Odłamki: niepełne elementy

**Odłamek** powstaje, gdy odczyt lub zapis od wyznaczonej pozycji sięga poza koniec bloku.

**Odczyt:** zmienna docelowa jest najpierw wypełniana zerami, a potem nakładane są na nią bajty istniejące w bloku, zaczynając od najmniej znaczącej części. Brakujące bajty zostają zerami w bardziej znaczącej części.

**Zapis:** do bloku trafiają tylko bajty, które w nim istnieją. Nadmiarowa część wartości jest odrzucana.

W obu przypadkach program reaguje zgodnie z `.rangeError`.

```
ptr.new[1023]                  # bajty 0–1022

x as float
x = ptr.float[255]             # od bajtu 1020: 3 bajty z bloku + 1 bajt zer

d as doublefloat
d = ptr.byte[1020]             # od bajtu 1020: 3 bajty z bloku + 5 bajtów zer
ptr.byte[1020] = d             # zapisane tylko 3 bajty (1020–1022)

y as float
y = ptr.float[500]             # od bajtu 2000: całkowicie poza blokiem, same zera
```

Odłamek typu `float` zwykle nie ma sensu liczbowego. To błąd założeń programisty (blok o złym rozmiarze). Zalecenie: przydzielaj bloki w jednostkach typu, z którym pracujesz, np. `new[1024*float]`.

---

## 11. Operacje blokowe

**Soczewka bez indeksu oznacza cały blok** jako ciąg elementów. Operacja wykonuje się na każdym elemencie:

```
ptr.float *= 2                              # każdy float w bloku razy 2
ptr.byte += 1                               # każdy bajt plus 1
ptr.float = 1.5                             # każdy float = 1.5
ptr.viewPortion[0:400].float *= 2           # tylko floaty w widoku
```

Zasada: **bez indeksu = całość, z indeksem = jeden element**.

`ptr.<typ>.count` zwraca liczbę **pełnych** elementów typu w bloku. Ostatni, niepełny element (odłamek) też jest objęty operacją, zgodnie z sekcją 10.

Kompilator zamienia operację blokową na pętlę w kodzie maszynowym, która przetwarza wiele elementów naraz instrukcjami wektorowymi (SIMD).

### Wypełnianie: `.fill`

`.fill[wartość]` wypełnia blok powtarzanym wzorem. Długość wzoru wyznacza ta sama reguła co wszędzie:

```
ptr.float.fill[1.5]      # z soczewką: powtarzany float (4 B)
ptr.fill[kolor]          # zmienna (kolor as Color): powtarzany 10-bajtowy piksel
ptr.fill[&00FFh]         # literał szesnastkowy: powtarzane 16 bitów
ptr.fill[&101b]          # literał binarny: powtarzane 3 bity
ptr.fill[5]              # literał dziesiętny bez soczewki: 1 bajt (sekcja 5)
```

**Wzór jest powtarzany z dokładnością do bitu**, także przez granice bajtów (`&101b` daje `101101101...`). Jeśli długość bloku w bitach nie dzieli się przez długość wzoru, ostatnie powtórzenie jest ucinane, zgodnie z zasadą odłamków.

`.clear` to to samo co `.fill[0]`.

---

## 12. Operacje bitowe i inne operacje wbudowane

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

Do języka trafia to, co odpowiada jednej instrukcji procesora albo wymaga wiedzy kompilatora, żeby działało szybko. Nazwy do ustalenia (sekcja 24):

- **liczenie bitów:** liczba jedynek, liczba zer od góry i od dołu (kompresja, kryptografia, struktury danych),
- **nasycenie `saturate( )`:** `250 + 10` w bajcie daje `255` zamiast zawinięcia do `4` (grafika: rozjaśnianie, mieszanie kolorów); opis w sekcji 4,
- **redukcje blokowe:** suma, minimum, maksimum, iloczyn skalarny dwóch bloków (podstawa uczenia maszynowego),
- **zamiana kolejności bajtów** dla plików i protokołów zapisanych w big-endian.

---

## 13. Widoki i kopie fragmentów

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

Widok ma wszystkie operacje bloku (soczewki, operacje blokowe, `.length`, `.fill`...) oprócz `.new`.

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

Każdy widok ma **własny wpis w menedżerze** (flaga `VIEW`) z własnym `.shares` i długością. W polu adresu wpis widoku przechowuje numer swojego **opisu w osobnej tablicy widoków**:

| Pole opisu | Rozmiar | Znaczenie |
|---|---|---|
| rodzic | 4 B | numer wpisu bloku, na który patrzy widok |
| przesunięcie | 8 B | początek widoku w bloku rodzica (w bajtach) |
| bajty wiersza | 8 B | szerokość jednego wiersza widoku |
| wiersze | 8 B | liczba wierszy |
| krok | 8 B | odległość między początkami wierszy w rodzicu |

**`viewPortion` to prostokąt z jednym wierszem**, więc jeden format opisu obsługuje oba kształty.

**Dostęp do danych:** adres rodzica (odczytany raz przed pętlą) + przesunięcie + numer wiersza × krok + pozycja w wierszu. Widok pamięta numer rodzica, a nie adres, więc po przeniesieniu rodzica przez `.update` nadal wskazuje właściwe miejsce.

**Widok widoku** jest przy tworzeniu zamieniany na widok bezpośrednio na oryginalny blok (przesunięcia się sumują). Dostęp to zawsze jeden poziom, bez łańcucha pośredników.

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

## 14. Pliki mapowane (`.map`)

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

---

## 15. Struktury (`STRUCT`)

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

---

## 16. Aliasy (`ALIAS`)

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

## 17. Wyjście poza blok: `.rangeError`

Dotyczy **wyłącznie bloków** (zmiennych `pointer` i widoków). Zmienne statyczne nie są sprawdzane (sekcja 4).

| Wartość | Tryb | Działanie |
|---|---|---|
| 0 | `DEFAULT` | zachowanie domyślne, ustawione przez `DEFAULT_RANGE_ERROR` |
| 1 | `CONTINUE` | program działa dalej, zgodnie z zasadami odłamków |
| 2 | `WARNING` | program działa dalej i zgłasza ostrzeżenie (sekcja 18) |
| 3 | `HALT` | program zatrzymuje się |

```
ptr.rangeError = 1                 # dla jednej zmiennej
DEFAULT_RANGE_ERROR = CONTINUE     # domyślnie dla całego programu
```

Standardowo `DEFAULT_RANGE_ERROR = HALT`. Tryb każdego bloku jest zapisany w bitach 8–9 jego wpisu w menedżerze.

---

## 18. Ostrzeżenia (`WARNING`)

**Kompilacja testowa:** kompilator dołącza zapisywanie ostrzeżeń do pliku logu obok programu (`nazwa_programu.warnings.log`). **Każde miejsce w kodzie zgłasza ostrzeżenie tylko raz**, a przy kolejnych wystąpieniach rośnie licznik. Na końcu programu w logu pojawia się podsumowanie, np. „linia 128: 999 999 kolejnych wystąpień”. Dzięki temu pętla wychodząca milion razy poza blok nie zaleje logu.

**Finalbake:** ostrzeżenia trafiają wyłącznie do funkcji obsługi zdefiniowanej przez programistę. Bez niej nie trafiają nigdzie.

```
WARNING_HANDLER = mojeOstrzezenia

FUNCTION mojeOstrzezenia(info as pointer): void
    ...    # np. pokaż w oknie, zapisz do bazy, wyślij na serwer
mojeOstrzezenia.end
```

Ostrzeżenie zawiera: numer bloku, pozycję dostępu, długość bloku, rodzaj dostępu (odczyt czy zapis) i miejsce w kodzie (plik i linia).

W finalbake bez `WARNING_HANDLER` tryb `WARNING` zachowuje się dokładnie jak `CONTINUE`, więc kompilator może wygenerować dla niego ten sam, najprostszy kod.

---

## 19. Zestawienie operacji na `pointer`

### Zarządzanie blokiem

| Operacja | Działanie |
|---|---|
| `ptr` | działa jak `ptr.pointer` |
| `ptr.pointer` | zwraca adres bloku |
| `ptr.new[*]` | rejestruje zmienną i przydziela pierwszy blok: `[rozmiar]` lub `[ilość*typ]`. Tylko raz. Nie zeruje bloku |
| `ptr.update[*]` | zmienia rozmiar, zachowując dane; nowe bajty mają nieokreśloną zawartość. Po `.release` przydziela nowy blok |
| `ptr.release` | zwalnia blok, `.length` = 0; zmienna pozostaje zarejestrowana. Niedozwolone przy aktywnych widokach |
| `ptr.clear` | zeruje cały blok (zawsze wykonywane, także tuż przed `.release`) |
| `ptr.fill[wartość]` | wypełnia blok powtarzanym wzorem (sekcja 11) |
| `ptr.map["plik"]` | podpina plik z dysku jako blok pamięci, tylko do odczytu |
| `ptr.map["plik", WRITABLE]` | podpina plik z dysku do odczytu i zapisu |
| `ptr.shares` | zwraca liczbę użyczeń |
| `ptr.length` | zwraca długość bloku w bajtach (0 = brak bloku) |
| `ptr.rangeError = <tryb>` | zachowanie przy wyjściu poza blok |
| `ptr.memoryPatternDebug = ON/OFF` | wypełnianie nowych bajtów wzorem w kompilacji testowej |
| `ptr.memoryPatternProduction = ON/OFF` | wypełnianie nowych bajtów wzorem w finalbake |

### Odczyt i zapis

| Operacja | Działanie |
|---|---|
| `ptr.value` | cały blok jako jedna liczba (największa soczewka) |
| `ptr.value = <wartość>` | zapisuje wartość od bajtu 0 |
| `ptr.<typ>[n]` | element przesunięty o n × rozmiar typu; szerokość według sekcji 9 |
| `ptr.<typ>` | bez indeksu: cały blok jako ciąg elementów (operacje blokowe) |
| `ptr.<typ>.count` | liczba pełnych elementów typu w bloku |
| `ptr.<Struktura>[n].pole` | pole struktury w n-tym elemencie, np. `ptr.Color[32].G` |

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

## 20. Kompilator

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

---

## 21. Język a biblioteka standardowa

> **Do języka trafia to, co odpowiada jednej instrukcji procesora albo wymaga wiedzy kompilatora, żeby działało szybko. Całe algorytmy idą do biblioteki standardowej.**

**W języku:** soczewki, operacje blokowe, operacje bitowe (sekcja 12), liczenie bitów, nasycenie (`saturate`), redukcje, zamiana kolejności bajtów, widoki i kopie.

**W bibliotece standardowej:** mnożenie macierzy, splot (konwolucja), FFT, szyfrowanie (AES), skróty (SHA), arytmetyka wielkich liczb (dodawanie i mnożenie bloków jako liczb), generatory liczb losowych, funkcje aktywacji sieci neuronowych, sortowanie.

Powody: algorytmów jest bardzo dużo, zmieniają się z czasem, a najlepsza implementacja zależy od sprzętu (CPU, karta graficzna, specjalne instrukcje procesora, np. dla AES). Biblioteka może z nich korzystać i być wymieniana bez zmiany języka, a sam język zostaje mały i łatwy do nauki.

---

## 22. Obiekty (plany)

Obiekty (klasy) zostaną opisane szczegółowo w osobnym etapie. Ustalone założenia:

- **Obiekty to struktury poza blokami**, z **własnym menedżerem pamięci**, odrębnym od menedżera bloków.
- **Przy usunięciu obiektu** menedżer obiektów zgłasza menedżerowi bloków, że obiekt odchodzi, a jego pola wskaźnikowe puszczają trzymane bloki. Menedżer bloków zmniejsza ich `.shares` i zwalnia te, których nikt inny nie używa.
- **Życie obiektu nie powinno wynikać ze zliczania odwołań między obiektami.** Gdyby tak było, dwa obiekty wskazujące na siebie nawzajem (np. samochód trzymający koło i koło znające swój samochód) trzymałyby się w pamięci na zawsze. Życie obiektu ma wynikać z właściciela (funkcji, programu lub obiektu, który go utworzył) albo z jawnego usunięcia przez programistę.
- **Słabe wskaźniki (`WEAK`)**, czyli wskaźniki, które „wiedzą, gdzie jest obiekt, ale go nie trzymają” (jak `TWeakObjectPtr` w Unreal Engine), zostaną rozważone przy projektowaniu klas. Jeśli będą potrzebne, ich mechanizm (np. licznik generacji wpisu) trafi do menedżera obiektów, a nie do menedżera bloków: bloki nie tworzą cykli, więc słabych wskaźników nie potrzebują.

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
    FUNCTION .Zwieksz(): void              # deklaracja
Licznik.end

FUNCTION Licznik.Zwieksz(): void           # definicja poza klasą, pełna nazwa
    .wartosc = .wartosc + 1                # pole tego obiektu (to samo co this.wartosc)
Zwieksz.end
```

- **Wewnątrz metody** `.pole` i `this.pole` oznaczają pole obiektu, na którym działa metoda. Zmienna bez kropki to zmienna lokalna metody, więc od razu widać, co jest polem.
- **Metody można definiować poza klasą** z pełną nazwą (`FUNCTION Klasa.Metoda`), w dowolnym miejscu pliku. Przy dużych klasach deklaracja klasy staje się czytelnym „spisem treści”.
- **Kropka na początku poza klasą to błąd kompilacji**, bo nie ma właściciela, do którego mogłaby się odnosić.
- `this` piszemy małymi literami, bo to odwołanie, używane jak zmienna, a nie słowo budujące strukturę programu.
- **Konstruktor:** obiekt musi mieć konstruktor z parametrami. Wstępna propozycja: parametry należą do konstruktora, a sama deklaracja klasy jest bez parametrów (`CLASS Klasa`). Do ustalenia.

---

## 23. Przykładowy program

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
    size = obraz.length

    obraz.Color[32].G = 500           # pole G w pikselu nr 32 (2 bajty)
    B = obraz.byte[320]               # pierwszy bajt piksela nr 32
    obraz.byte[1009] = d              # 8 bajtów od bajtu 1009

    # widok na kafelek 64 × 64 od piksela (100, 50), bez kopiowania
    kafelek as pointer
    kafelek = obraz.viewRectangle[100*Color, 50, 64*Color, 64, SZER*Color]
    kafelek.Color.fill[obraz.Color[0]]

    # kopia tego samego obszaru do nowego bloku
    miniatura as pointer
    miniatura = obraz.copyRectangle[100*Color, 50, 64*Color, 64, SZER*Color]

    kafelek.release                   # najpierw widok...
    flagi.new[2]
    isLightEnabled = true

    obraz.byte xor= &FFh              # każdy bajt odwrócony
    obraz.byte = saturate(obraz.byte + 20)   # rozjaśnienie bez „przekręcania” jasnych bajtów

    if BUILD_MODE = TEST then
        size = potega(2, 10)
    if.end

    obraz.release                     # ...potem blok (nie ma już widoków)
    obraz.update[100*float]           # nowy blok 400 bajtów, zawartość nieokreślona
    obraz.float = 1                   # wypełnienie wszystkich floatów
    obraz.float *= 2                  # operacja blokowa
MAIN END

FUNCTION potega(base as float, times as int): float
    temp as float = 1
    for i = 1 to times do
        temp = temp * base
    for.end
    return temp
potega.end
```

---

## 24. Otwarte pytania

- [ ] **Klasy i obiekty:** konstruktor i jego parametry, `PRIVATE`, tworzenie i usuwanie obiektów, menedżer obiektów, sposób ustalania życia obiektu, ewentualne `WEAK` (sekcja 22).
- [ ] **Praca równoległa:** `for.parallel`, `split.chunk`, `split.cores`, tryby widoków (`read` / `write`).
- [ ] **Nazwy operacji wbudowanych:** liczenie bitów, redukcje (suma, min, max, iloczyn skalarny), zamiana kolejności bajtów.
- [ ] **Podmiana funkcji w działającym programie** (cel na przyszłość, sekcja 20).
- [ ] **Środowisko programistyczne:** podpowiedzi (np. szerokość literału), menu trybów kompilacji, podgląd logu ostrzeżeń.
