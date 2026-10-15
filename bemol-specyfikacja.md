# BEMOL ♭ — specyfikacja języka

> **BEMOL**: *Boundless Efficient Machine-Oriented Language*
> Repozytorium: `github.com/bemol-lang/bemol` · rozszerzenie plików: `.bmol`
> Status: **szkic roboczy** · ostatnia aktualizacja: 2026-10-15

BEMOL to kompilowany język do szybkiego przetwarzania dużych bloków danych. Daje dostęp do pamięci z precyzją asemblera (każdy bajt, każdy bit), ale z czytelną składnią i automatycznym zarządzaniem pamięcią.

**Dlaczego „bemol”?** Bemol (♭) w muzyce obniża dźwięk. C# poszło „w górę”, ku wysokiemu poziomowi abstrakcji. BEMOL schodzi „w dół”, bliżej sprzętu, do bitów i bajtów.

---

## Spis treści

1. [Filozofia](#1-filozofia)
2. [Składnia ogólna](#2-składnia-ogólna)
3. [Typy i rozmiary](#3-typy-i-rozmiary)
4. [Typ `pointer`](#4-typ-pointer)
5. [Cykl życia bloku](#5-cykl-życia-bloku)
6. [Menedżer pamięci i `.shares`](#6-menedżer-pamięci-i-shares)
7. [Soczewki: pozycja i szerokość](#7-soczewki-pozycja-i-szerokość)
8. [Odłamki: niepełne elementy](#8-odłamki-niepełne-elementy)
9. [Operacje blokowe](#9-operacje-blokowe)
10. [Struktury (`STRUCT`)](#10-struktury-struct)
11. [Aliasy (`ALIAS`)](#11-aliasy-alias)
12. [Wyjście poza blok: `.rangeError`](#12-wyjście-poza-blok-rangeerror)
13. [Literały](#13-literały)
14. [Zestawienie operacji na `pointer`](#14-zestawienie-operacji-na-pointer)
15. [Przykładowy program](#15-przykładowy-program)
16. [Otwarte pytania](#16-otwarte-pytania)

---

## 1. Filozofia

**Wszystko jest blokiem pamięci.** Blok sam w sobie nie ma typu. Typ to **soczewka**, przez którą patrzymy na fragment bloku. Ten sam blok można w jednym programie czytać bajtami, liczbami, strukturami czy bitami.

**Jedna notacja.** Wszystkie operacje na zmiennej zapisuje się po kropce: `nazwa.operacja`.

**Czytelnie dla człowieka, szybko dla maszyny.** Nazwy mówią wprost, co robią (np. wszystko, co kopiuje dane, ma w nazwie `copy`).

**Co ma kosztować zero, musi być znane podczas kompilacji.** Rozmiary typów, stałe `CONST`, aliasy i struktury są ustalone przed uruchomieniem programu i kompilator po prostu je podstawia. Elastyczność dają zmienne, indeksy i okna.

**Kolejność bajtów: little-endian.** Bajt 0 jest najmniej znaczący. Blok czytamy jak zapis binarny, „od prawej do lewej”. To naturalny porządek procesorów x86 i ARM.

**Indeksowanie od zera.**

---

## 2. Składnia ogólna

### Wielkość liter

Język rozróżnia wielkość liter.

- **Słowa kluczowe budujące strukturę programu lub decydujące o życiu zmiennych piszemy WIELKIMI literami** (wymagane): `MAIN`, `BEGIN`, `END`, `CLASS`, `FUNCTION`, `STRUCT`, `GLOBAL`, `PERSISTENT`, `CONST`, `ALIAS`, `PRIVATE`.
- **Słowa przepływu sterowania i łączniki piszemy małymi literami:** `for`, `to`, `do`, `if`, `then`, `as`, `return`.
- **Wieloczłonowe nazwy wbudowane w język** piszemy z wielką literą na początku kolejnych słów: `rangeError`, `copyPortion`.
- **Nazwy zmiennych, funkcji i klas programisty są dowolne.**

### Zamykanie bloków

Każdy blok zamyka się swoją nazwą z przyrostkiem `.end`:

```
for i = 1 to 10 do
    ...
for.end

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

- **Zmienne o stałym rozmiarze** (`int`, `float`, `byte`...) trafiają na **stos**. Procesor przydziela i zwalnia miejsce dla nich jedną instrukcją przy wejściu do funkcji i wyjściu z niej, więc kosztują praktycznie zero. Każde wywołanie funkcji, także rekurencyjne, ma własne kopie.
- **Zmienne `pointer`** mają blok na **stercie** i wpis w menedżerze pamięci (sekcja 6).

---

## 3. Typy i rozmiary

Rozmiary są stałe i zdefiniowane przez język, niezależnie od procesora.

| Rodzaj | Typ | Rozmiar |
|---|---|---|
| bit | `bit` | 1/8 bajta |
| bez znaku | `byte` = `unsigned_8` | 1 B |
| | `unsigned_16` | 2 B |
| | `unsigned_32` | 4 B |
| | `unsigned_64` | 8 B |
| ze znakiem | `shortint` | 2 B |
| | `int` | 4 B |
| | `longint` | 8 B |
| zmiennoprzecinkowe | `halffloat` | 2 B |
| | `float` | 4 B |
| | `doublefloat` | 8 B |
| struktura | `STRUCT` | suma pól (sekcja 10) |

**Nazwa typu w wyrażeniu liczbowym oznacza jego rozmiar w bajtach:**

```
ptr.new[1024*float]          # 4096 bajtów
img.new[1920*1080*Color]     # struktury też mają rozmiar
```

**Najmniejsza jednostka przydziału pamięci to 1 bajt:**

- w wyrażeniach rozmiaru wynik z bitami zaokrągla się w górę: `new[100*bit]` = 13 bajtów,
- pojedyncza zmienna `b as bit` zajmuje w pamięci cały bajt, ale przyjmuje tylko wartości 0/1 (tożsame z `false`/`true`).

Do oszczędnego przechowywania wielu flag służy blok i soczewka `.bit`: `flagi.new[1000*bit]` zajmuje 125 bajtów.

---

## 4. Typ `pointer`

`pointer` to zmienna wskazująca na blok pamięci przydzielany dynamicznie. Daje dostęp do każdego bajtu i bitu bloku i jest objęta automatycznym zarządzaniem pamięcią.

```
ptr as pointer
GLOBAL ptr as pointer
```

Zadeklarowana zmienna nie ma jeszcze bloku: `ptr.length` zwraca 0.

**Przypisanie wskaźnika** (`ptr2 = ptr`) kopiuje tylko wskaźnik: obie zmienne wskazują ten sam blok, a jego `.shares` rośnie o 1. Kopię danych tworzy wyłącznie `.copy` lub `.copyPortion`.

Gdy zmienna `pointer` dostaje nowy blok (np. `glb = mojaFunkcja()`), `.shares` jej poprzedniego bloku maleje o 1, a pamięć jest zwalniana, gdy licznik spadnie do 0.

---

## 5. Cykl życia bloku

### `.new` — rejestracja

**Rejestruje zmienną w menedżerze pamięci** i przydziela pierwszy blok. Można jej użyć **tylko raz w życiu zmiennej**. Rozmiar podaje się w bajtach lub jako `ilość*typ`.

```
ptr.new[1024]
ptr.new[100*int]
```

### `.update` — zmiana rozmiaru

Zmienia rozmiar bloku, **zachowując istniejące dane**. Nowo dodane bajty są **zerowane**. Po `.release` przydziela nowy, wyzerowany blok.

### `.release` — zwolnienie pamięci

Zwalnia blok i ustawia `.length` na 0. **Rejestracja zmiennej przeżywa `.release`**: inna część programu, która trzyma tę zmienną, nie dostaje wskaźnika donikąd, tylko widzi `.length = 0`, a odczyt zachowuje się zgodnie z `.rangeError`.

```
.new  ──►  [ .update  ⇄  .release ]  ──►  koniec życia zmiennej
(raz)       (dowolnie wiele razy)
```

### Zmienne `pointer` w funkcjach

**Zwykła zmienna** dostaje nowy wpis w menedżerze przy każdym wywołaniu funkcji.

**Zmienna `PERSISTENT`** ma w menedżerze zarezerwowany wpis, gotowy przy każdym wywołaniu funkcji. Oszczędza to koszt rejestracji w funkcjach wywoływanych bardzo często. **Adres i zawartość bloku nie są gwarantowane** między wywołaniami: trwałe jest miejsce w menedżerze, nie dane.

```
FUNCTION przetwarzaj(): void
    everyTimeNew as pointer
    PERSISTENT onceAndFast as pointer
przetwarzaj.end
```

**Na końcu funkcji sprawdzane jest `.shares` bloku `PERSISTENT`:**

- **0**: blok był używany tylko w funkcji, wpis jest zerowany i czeka na kolejne wywołanie,
- **większe od 0**: blok „uciekł” z funkcji (zwrócony, przypisany do zmiennej globalnej, zapisany w innym bloku). Odłącza się od trybu `PERSISTENT` i staje zwykłym blokiem nowego właściciela, a funkcja dostanie nowy wpis przy następnym wywołaniu.

**Rekurencja:** gdy wpis `PERSISTENT` jest zajęty przez trwające wywołanie, kolejne wywołanie dostaje zwykły blok. `PERSISTENT` to optymalizacja, więc w trudnym przypadku z niej rezygnuje, a program działa poprawnie.

---

## 6. Menedżer pamięci i `.shares`

### Tablica przydziałów

Menedżer pamięci to **tablica dynamiczna**, w której każdy wiersz opisuje jeden przydział. **Numer wiersza jest identyfikatorem bloku**: zmienna `pointer` przechowuje tylko ten numer (4 bajty). Dostęp do wpisu jest natychmiastowy (początek tablicy + numer × rozmiar wpisu). Numery po zwolnionych przydziałach są ponownie wykorzystywane dzięki liście wolnych miejsc.

| Pole | Rozmiar | Opis |
|---|---|---|
| adres | 8 B | położenie bloku w pamięci |
| długość | 8 B | rozmiar bloku w bajtach (do 2^64 B ≈ 16 milionów TB) |
| shares | 4 B | liczba użyczeń |
| flagi | 4 B (32 bity) | m.in. `PERSISTENT`, `GLOBAL` |

**Wpis ma 24 bajty** (wyrównanie do 8 bajtów). Milion jednoczesnych bloków to 24 MB.

Gdy `.update` musi przenieść blok w inne miejsce, zmienia się tylko adres we wpisie. Wszystkie zmienne wskazujące ten przydział od razu widzą nowy adres.

### Liczba użyczeń `.shares`

- gdy element programu (funkcja, pętla, program główny) zaczyna używać bloku, `.shares` rośnie o 1,
- przypisanie `ptr2 = ptr` zwiększa `.shares` o 1,
- okno (`.window`) zwiększa `.shares` swojego rodzica,
- gdy element programu się kończy, `.shares` maleje o 1,
- **gdy `.shares` osiągnie 0, pamięć jest zwalniana automatycznie.**

Zmienna `GLOBAL` należy do programu głównego, więc jej `.shares` nie spadnie do 0 przed końcem programu. Pamięć można zwolnić wcześniej ręcznie, przez `.release`.

---

## 7. Soczewki: pozycja i szerokość

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
```

Soczewka służy więc do **ustawienia pozycji**, a druga strona mówi, **ile miejsca zajmują dane**. Dzięki temu można zapisać lub odczytać wartość dowolnego typu od dowolnego miejsca: `ptr.byte[1009] = d`.

**Ostrzeżenie kompilatora:** gdy druga strona jest szersza niż soczewka (np. `int` z soczewką `.byte`), kompilator zgłasza ostrzeżenie, np. „zapis 4 bajtów przez soczewkę 1-bajtową”. Kod działa zgodnie z regułą 1, a ostrzeżenie pomaga wychwycić przypadkowe nadpisanie sąsiednich bajtów. Można je wyłączyć.

---

## 8. Odłamki: niepełne elementy

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

## 9. Operacje blokowe

**Soczewka bez indeksu oznacza cały blok** jako ciąg elementów. Operacja wykonuje się na każdym elemencie:

```
ptr.float *= 2                       # każdy float w bloku razy 2
ptr.byte += 1                        # każdy bajt plus 1
ptr.window[0:400].float *= 2         # tylko floaty w oknie
ptr.window[0:32*Color].Color = tlo   # pierwsze 32 kolory
```

Zasada: **bez indeksu = całość, z indeksem = jeden element**.

`ptr.<typ>.count` zwraca liczbę **pełnych** elementów typu w bloku. Ostatni, niepełny element (odłamek) też jest objęty operacją, zgodnie z sekcją 8.

Kompilator zamienia operację blokową na pętlę w kodzie maszynowym, która przetwarza wiele elementów naraz instrukcjami wektorowymi (SIMD).

---

## 10. Struktury (`STRUCT`)

**Struktura to zestaw aliasów ze stałymi przesunięciami**, a nie pudełko na dane jak w C. Deklaracja nie przydziela pamięci, tylko mówi kompilatorowi, gdzie leżą pola względem początku struktury.

```
Color as STRUCT { R as unsigned_16, G as unsigned_16, B as unsigned_16, Alpha as unsigned_32 }
```

- **Struktura jest „ciasna”:** jej rozmiar to dokładnie suma pól, bez pustych bajtów wyrównania. `Color` = 2+2+2+4 = **10 bajtów**.
- **Nazwa struktury działa jak każdy typ**: w wyrażeniach rozmiaru (`new[100*Color]`) i jako soczewka.
- **Struktura nie jest właścicielem danych.** Blok dalej należy do zmiennej `pointer` i można go czytać innymi strukturami, bajtami czy bitami.
- Przesunięcia są stałe, więc struktura **nic nie kosztuje** w działającym programie.

```
ptr.new[100*Color]
ptr.Color[32].G = 500          # pole G w pikselu nr 32
x = ptr.Color[32].G            # to samo co: x = ptr.unsigned_16[...] od bajtu 322
```

---

## 11. Aliasy (`ALIAS`)

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

## 12. Wyjście poza blok: `.rangeError`

| Wartość | Tryb | Działanie |
|---|---|---|
| 0 | `DEFAULT` | zachowanie domyślne, ustawione przez `DEFAULT_RANGE_ERROR` |
| 1 | `CONTINUE` | program działa dalej, zgodnie z zasadami odłamków |
| 2 | `WARNING` | program działa dalej i zgłasza ostrzeżenie |
| 3 | `HALT` | program zatrzymuje się |

```
ptr.rangeError = 1                 # dla jednej zmiennej
DEFAULT_RANGE_ERROR = CONTINUE     # domyślnie dla całego programu
```

Standardowo `DEFAULT_RANGE_ERROR = HALT`.

W trybie debug ostrzeżenia `WARNING` trafiają do konsoli lub środowiska programistycznego.

---

## 13. Literały

**Literał** to wartość zapisana wprost w kodzie.

```
5          # literał dziesiętny
&FF0ACh    # literał szesnastkowy (20 bitów)
&0111001b  # literał binarny (7 bitów)
```

- Literał jest zapisywany od wskazanej pozycji w porządku little-endian: najmniej znacząca część trafia na najniższą pozycję. `ptr.byte[0] = &FF00h` daje bajt 0 = `00`, bajt 1 = `FF`.
- **Literał szesnastkowy i binarny zmienia dokładnie tyle bitów, ile ma zapis**, a nie do pełnego bajtu.
- **Literał dziesiętny przyjmuje szerokość soczewki** (sekcja 7).

---

## 14. Zestawienie operacji na `pointer`

### Zarządzanie blokiem

| Operacja | Działanie |
|---|---|
| `ptr` | działa jak `ptr.pointer` |
| `ptr.pointer` | zwraca adres bloku |
| `ptr.new[*]` | rejestruje zmienną i przydziela pierwszy blok: `[rozmiar]` lub `[ilość*typ]`. Tylko raz |
| `ptr.update[*]` | zmienia rozmiar, zachowując dane; nowe bajty są zerowane. Po `.release` przydziela nowy blok |
| `ptr.release` | zwalnia blok, `.length` = 0; zmienna pozostaje zarejestrowana |
| `ptr.clear` | zeruje cały blok |
| `ptr.fill[wartość]` | wypełnia blok powtarzaną wartością (`clear` = `fill[0]`) |
| `ptr.copy` | zwraca nowy, niezależny blok z kopią całej zawartości |
| `ptr.map["plik"]` | podpina plik z dysku jako blok pamięci |
| `ptr.shares` | zwraca liczbę użyczeń |
| `ptr.length` | zwraca długość bloku w bajtach (0 = brak bloku) |
| `ptr.rangeError = <tryb>` | zachowanie przy wyjściu poza blok |

### Odczyt i zapis

| Operacja | Działanie |
|---|---|
| `ptr.value` | zwraca zawartość całego bloku |
| `ptr.value = <wartość>` | zapisuje wartość od bajtu 0 |
| `ptr.<typ>[n]` | element przesunięty o n × rozmiar typu; szerokość według sekcji 7 |
| `ptr.<typ>` | bez indeksu: cały blok jako ciąg elementów (operacje blokowe) |
| `ptr.<typ>.count` | liczba pełnych elementów typu w bloku |
| `ptr.<Struktura>[n].pole` | pole struktury w n-tym elemencie, np. `ptr.Color[32].G` |

### Fragmenty (pozycje i długości w bajtach)

| Operacja | Działanie |
|---|---|
| `ptr.copyPortion[od:ile]` | zwraca **kopię** `ile` bajtów od bajtu `od` |
| `ptr.window[od:ile]` | zwraca **okno** na ten sam obszar, bez kopiowania. Okno zwiększa `.shares` rodzica i ma wszystkie operacje z tej tabeli oprócz `.new` |

Wszystko, co zaczyna się od `copy`, tworzy nowe dane. Pozostałe operacje działają na istniejących.

---

## 15. Przykładowy program

```
GLOBAL ptr as pointer
GLOBAL flagi as pointer

CONST ROZMIAR as int = 1024
CONST LIGHT_BIT as int = 7

Color as STRUCT { R as unsigned_16, G as unsigned_16, B as unsigned_16, Alpha as unsigned_32 }

ALIAS isLightEnabled as flagi.bit[LIGHT_BIT]

MAIN BEGIN
    size as longint
    B as byte
    d as doublefloat = 3.14

    ptr.new[ROZMIAR*Color]       # 10 240 bajtów
    ptr.clear
    size = ptr.length            # 10240

    ptr.Color[32].G = 500        # pole G w pikselu nr 32 (2 bajty)
    B = ptr.byte[320]            # pierwszy bajt piksela nr 32
    ptr.byte[1009] = d           # 8 bajtów od bajtu 1009

    flagi.new[2]
    isLightEnabled = true

    ptr.rangeError = 1           # CONTINUE
    ptr.update[1]                # blok ma teraz 1 bajt
    B = ptr.byte[1]              # poza blokiem: 0, program działa dalej

    ptr.release                  # length = 0, zmienna nadal zarejestrowana
    ptr.update[100*float]        # nowy, wyzerowany blok 400 bajtów
    ptr.float *= 2               # operacja blokowa

    size = potega(2, 10)
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

## 16. Otwarte pytania

- [ ] **Cykle w `.shares`:** blok A wskazuje na B, a B na A. Ich `.shares` nigdy nie spadnie do 0, co oznacza wyciek pamięci. Możliwe rozwiązanie: słabe wskaźniki, które nie zwiększają `.shares`.
- [ ] **`WARNING` w gotowym programie:** gdzie i jak zgłaszać ostrzeżenia poza trybem debug (plik logu, kanał błędów, konfiguracja).
- [ ] **Wpis okna w menedżerze pamięci:** okno musi znać swojego rodzica i przesunięcie, żeby po przeniesieniu rodzica przez `.update` wskazywać właściwe miejsce. Prawdopodobnie potrzebne pole z numerem rodzica.
- [ ] **Dodatkowe flagi menedżera:** `MAPPED` (blok to plik z `.map`), `WINDOW` (wpis jest oknem).
- [ ] **Działania na różnych typach:** jaki typ ma wynik `ptr.byte[5] + ptr.byte[6]` (czy 200 + 100 mieści się w bajcie?) i co przy mieszaniu typów, np. `int` z `float`.
- [ ] **Szerokość `.fill[wartość]`:** czy powtarzany wzorzec ma szerokość według sekcji 7.
- [ ] **Klasy:** pola, metody, `PRIVATE`, tworzenie obiektów.
- [ ] **Praca równoległa:** `for.parallel`, `split.chunk`, `split.cores`, tryby okien (`read` / `write`).
- [ ] **Kompilacje cząstkowe:** podział programu na osobno kompilowane bloki i finalne łączenie.
