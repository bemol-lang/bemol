# BEMOL ♭ — prototyp tłumacza (wersja 0.3)

Pierwszy działający BEMOL: tłumacz z BEMOL-a na C oraz biblioteka menedżera bloków.
Cel wersji 0 to **sprawdzenie, czy model bloków, soczewek i widoków działa tak, jak opisuje specyfikacja**, a nie szybkość.

```
program.bmol ──► bemolc.py ──► program.c ──► gcc ──► program
                                   │
                              bemol_rt.h (menedżer bloków)
```

## Wymagania

- Python 3.8 lub nowszy,
- kompilator C: **GCC** (albo clang). Tłumacz zamienia BEMOL na C, a dopiero GCC robi z tego program.

### Instalacja GCC na Windows

1. Otwórz terminal (PowerShell albo Wiersz polecenia).
2. Wpisz:
   ```
   winget install BrechtSanders.WinLibs.POSIX.UCRT
   ```
3. **Zamknij terminal i otwórz go na nowo**, żeby Windows zobaczył nowy kompilator.
4. Sprawdź: `gcc --version` powinno wypisać wersję GCC.

Linux: `sudo apt install gcc`. macOS: `xcode-select --install`.

Gdy kompilatora brakuje, tłumacz zgłasza błąd **BML-E0998** z tą samą instrukcją.

## Użycie

Z folderu `prototyp/przyklady`:

```
python3 ../bemolc.py tekstura.bmol         # kompilacja testowa
tekstura.exe                               # uruchomienie na Windows (Linux/macOS: ./tekstura)
```

Na Windows najprościej przez `bemol.bat` (kompiluje i od razu uruchamia program):

```
..\bemol tekstura.bmol
..\bemol -finalbake tekstura.bmol
```

Folder `prototyp` można dodać do zmiennej PATH, wtedy wystarczy `bemol program.bmol` w każdym folderze.

Rozszerzenie BEMOL dla VS Code korzysta z tego samego tłumacza: `Ctrl+F5` kompiluje i uruchamia, a błędy pojawiają się w edytorze przy zapisie.

Wszystkie opcje:

```
python3 bemolc.py program.bmol             # kompilacja testowa → program (.exe na Windows)
python3 bemolc.py -finalbake program.bmol  # finalbake (pełna optymalizacja kompilatora C)
python3 bemolc.py --check program.bmol     # tylko sprawdzenie kodu, bez kompilatora C
python3 bemolc.py -diagnostics=json program.bmol   # komunikaty dla narzędzi: jedna linia JSON na komunikat
python3 bemolc.py --check program.bmol     # tylko sprawdzenie kodu, bez kompilatora C
python3 bemolc.py -diagnostics=json program.bmol   # komunikaty dla narzędzi: jedna linia JSON na komunikat
python3 bemolc.py --emit-c program.bmol    # tylko wygenerowany kod C (program.c)
python3 bemolc.py --debug program.bmol     # pełny ślad Pythona przy błędzie wewnętrznym tłumacza
```

Tłumacz nigdy nie powinien kończyć się surowym śladem Pythona. Jeśli tak się stanie, to błąd prototypu: zgłoś go razem z plikiem `.bmol`.

## Pliki

| Plik | Zawartość |
|---|---|
| `bemolc.py` | tłumacz: lekser, parser, generator kodu C, komunikaty błędów |
| `bemol.bat` | Windows: kompilacja i uruchomienie jednym poleceniem |
| `bemol_rt.h` | biblioteka wykonawcza: menedżer bloków (wpisy 32 B), widoki, odczyt/zapis z odłamkami, `.rangeError`, wypisywanie |
| `przyklady/widok10x10.bmol` | przykład 10 × 10 z `bemol-wnetrze.md`, rozdział 5 |
| `przyklady/tekstura.bmol` | obraz 256 × 256 pikseli `Color`: widoki, kopie, `foreach`, `saturate`, funkcje |
| `przyklady/petle.bmol` | typowane liczniki `for`, licznik zadeklarowany przed pętlą, zamiana `as` |
| `przyklady/menu.bmol` | interaktywne menu z `keyInput`: tekst i liczby z klawiatury, `.update`, `.fill`, zrzut |
| `przyklady/wejscie.bmol` | `INPUT.read[bufor]`: czytanie wejścia porcjami (`wejscie < plik.txt`) |
| `przyklady/zasady.bmol` | zasady arytmetyki i soczewek Z1–Z5: stół 64-bitowy, worek przy zapisie, `.at`, literał dłuższy niż soczewka |
| `przyklady/wybor.bmol` | `switch` / `case`: listy, zakresy, `CONST`, `@ANYTHING_ELSE`, `@ACCEPT WARNING`, `break` w gałęzi |
| `przyklady/funkcje.bmol` | uprawnienia funkcji do bloku: `CONST`, bez znacznika, `REF` (zmiana rozmiaru, podmiana, `.release`) |
| `przyklady/blad_*.bmol` | przykłady komunikatów błędów |

## Co obsługuje prototyp

- **typy:** `byte`, `unsigned_8/16/32/64`, `signed_8`, `shortint`, `int`, `longint`, `float`, `doublefloat`, `bit`, `pointer`, `text`,
- **deklaracje:** zmienne, `GLOBAL`, `CONST`, `STRUCT` (pola o pełnych bajtach), `ALIAS`, `blok as pointer.new[1024]` (deklaracja z przydziałem),
- **bloki:** `.new`, `.update`, `.release`, `.clear`, `.fill`, `.size`, `.shares`, `.rangeError`,
- **arytmetyka (sekcja 5, Z1–Z2):** działania na 64 bitach (`doublefloat`, gdy w działaniu jest ułamek), dopasowanie do typu zmiennej lub soczewki dopiero przy zapisie: `(a + b) / 2` dla bajtów 200 i 200 daje 200, `if a + b > 255` działa, `7.9 + 0.5` do `int` daje 8,
- **soczewki (sekcja 10, Z3–Z5):** `ptr.<typ>[n]` czyta i pisze zawsze swoją szerokość, `ptr.<typ>.at[n]` (pozycja w bajtach), pola struktur `ptr.Color[n].G`, literał dłuższy niż soczewka zawija się z ostrzeżeniem BML-W0120, liczba dziesiętna jako wzór `.fill` bez soczewki to błąd,
- **operacje blokowe:** `ptr.byte += 1`, `ptr.float = 1.5`, `ptr.byte = saturate(ptr.byte + 60)`, także `xor=`, `shl=` itd.,
- **widoki i kopie:** `viewPortion`, `viewRectangle`, `copy`, `copyPortion`, `copyRectangle`, przypisanie widoku do widoku (kopia danych),
- **liczniki:** `.shares` i liczba widoków, zwalnianie bloku na końcu zasięgu, zakaz `.release` bloku z aktywnymi widokami,
- **sterowanie:** `if`/`elseif`/`else`, `while`, `repeat...until`, `break`, `continue`, separator `;`,
- **`switch` / `case`:** kilka wartości po przecinku, zakresy `to`, stałe `CONST`, `@ANYTHING_ELSE` (samo albo na liście, tylko raz), pierwsza pasująca gałąź wygrywa, ostrzeżenia o szczególnym przypadku przed ogólnym (W0310) i o martwej gałęzi (W0311), błąd przy `else` w `switch`; `break` w gałęzi przerywa pętlę,
- **`@ACCEPT WARNING`** na końcu instrukcji ukrywa jej ostrzeżenia; zbędne `@ACCEPT` daje ostrzeżenie W0002,
- **`for` z typowanym licznikiem:** `for i as int = 0 to 99 [step s] do` (nowa zmienna pętli, znika po `for.end`) albo `for i = ...` dla zmiennej zadeklarowanej wcześniej (zostaje w niej ostatnia wartość); wewnętrzny licznik 64-bitowy, zakres sprawdzany raz przed pętlą (dla literałów już przy kompilacji), krok 0 to błąd,
- **`foreach px, nr as int in blok.T`** (numer elementu z jawnym typem),
- **zamiana `as`:** `wartosc as byte` (najmłodsza część), `x as int` (ułamek odcięty), `as bit`; wiąże mocniej niż `+` i `*`,
- **wejście:** `keyInput("tekst", REF zmienna, ...)` (linia do 255 B, sprawdzanie typu i zakresu z ponowieniem, tekst dostaje dokładnie tyle bajtów, ile wpisano; `keyInput()` czeka na Enter), `n = INPUT.read[bufor]` (zwraca liczbę przeczytanych bajtów, 0 = koniec danych),
- **funkcje (sekcja 3):** parametry liczbowe kopiowane, bloki przez wskaźnik; trzy poziomy uprawnień do bloku: `CONST` (tylko odczyt, obowiązuje także w wywoływanych funkcjach i w widokach), bez znacznika (zmiana danych), `REF` (także `.new`, `.update`, `.release`, `.append`, podmiana); `REF` po obu stronach; błąd, gdy ten sam blok trafia do dwóch parametrów; funkcja bez wyniku nie ma nic po nawiasie,
- **teksty:** `t as text = "..."`, `.length`, `.size`, `.append[...]`, porównanie `==` treści,
- **wypisywanie:** `print`, `println`, formaty `: hex`, `: bin`, `: N`, zrzut bloku `println(blok : hex)`,
- **`BUILD_MODE`**, `return` z kodem zakończenia w `MAIN`, `saturate( )`, `rol`/`ror`.

## Czego jeszcze nie ma

`ENUM`, klasy, `PERSISTENT`, `.map`, `.value` (cały blok jako liczba), typy o nietypowej szerokości (`unsigned_12`) i pola bitowe w strukturach, `halffloat`, wzory pamięci, `@ACCEPT RUNTIME_ERROR`, zwracanie kilku wartości, `ARGS`, praca równoległa.
Użycie któregokolwiek z nich daje czytelny błąd **BML-E0900** zamiast złego tłumaczenia.

Optymalizacje z rozdziału 9 dokumentu o wnętrzu (adres raz przed pętlą, sprawdzanie zakresu raz przed pętlą) **nie są jeszcze zrobione**: każdy dostęp przechodzi przez menedżer. Pomiary szybkości mają sens dopiero w następnej wersji.

## Wyniki testów

**`widok10x10.bmol`** (zgodne z `bemol-wnetrze.md`):

```
Bajty widoku (k = 0...11): 32 33 34 35 42 43 44 45 52 53 54 55
kafelek.byte[5] = 43   (oczekiwane: 43)
Zrzut widoku, wiersz po wierszu:
000000: 20 21 22 23
000004: 2A 2B 2C 2D
000008: 34 35 36 37
```

**`tekstura.bmol`**: piksel (100, 50) ma R = 25600 i G = 12800, kafelek 4 × 2 piksele ma 80 B, zapis przez widok zmienia obraz, a kopia `copyRectangle` zostaje nietknięta, `saturate` nie „przekręca” bajtów, suma R w kafelku wynosi dokładnie 316 408, `REF` zamienia zmienne.

**`petle.bmol`**: `for i = 1 to 10 step 3` zostawia w `i` wartość 10, licznik `byte` przechodzi cały zakres 0...255 (suma 32640), `1000 as byte` = 232, `3.99 as int` = 3, `blok.byte[n] = (n * 16 + n) as byte` zapisuje po 1 B.

**`menu.bmol`**: błędne wpisy (`abc`, `300` dla `byte`, linia dłuższa niż 255 B) są odrzucane z prośbą o ponowienie; koniec wejścia daje błąd BML-E0130.

**`wejscie.bmol`**: dla pliku 1017 B i 33 linii wypisuje dokładnie te liczby (zgodne z `wc`).

**`zasady.bmol`**: średnia bajtów 200 i 200 = 200, `a + b` do `byte` = 144, `a + b > 255` prawdziwe, `7.9 + 0.5` do `int` = 8, `7 / 2 + 0.5` = 4, `x as int = blok.byte[5]` czyta 1 bajt, `blok.byte[2] = 300` zapisuje 44 bez ruszania sąsiada, `.at` zapisuje i czyta `unsigned_16` i `doublefloat` od dowolnego bajtu, `a.byte[0] = &1234h` zapisuje `34` z ostrzeżeniem.

**`funkcje.bmol`**: `CONST` tylko czyta, funkcja bez znacznika zmienia dane, `REF` zmienia rozmiar, podmienia blok (stary blok traci jedno `shares`) i go zwalnia.

**Przykład z sekcji 27 specyfikacji** kompiluje się i działa bez zmian.

**Komunikaty błędów** (format z sekcji 20 specyfikacji):

```
*****************************************************************
ERROR: BML-E0420
blad_ref.bmol
at line 9, column 5
-----------------------------------------------------------------
9 |     dane.update[32]
  |     ^
-----------------------------------------------------------------
  [ ! ] .update zmienia wpis bloku „dane” w menedżerze, a parametr nie ma REF
  [ i ] bez REF funkcja może zmieniać dane bloku, ale nie jego rozmiar, adres ani istnienie
[ tip ] dodaj REF w deklaracji funkcji (dane → REF dane) i przy wywołaniu
_________________________________________________________________
```

Pozostałe przykłady błędów: `blad_const` (zapis do `CONST`), `blad_const2` (`CONST` przekazane dalej), `blad_dwa` (ten sam blok w dwóch parametrach), `blad_end` (`zmienREF.end` zamyka funkcję `zmien`), `blad_literal` (`&FF` bez `h`), `blad_fill` (`.fill[256]` bez soczewki), `blad_licznik`, `blad_zakres`, `blad_petla`, `blad_warunek`, `blad_widoki`.

Błędy w czasie działania programu (np. BML-E0412, BML-E0206) mają tę samą ramkę, bez linii kodu.

## Odkrycia z prototypu (już rozstrzygnięte w specyfikacji)

1. **`blok.byte[i] = i` zapisywało 8 bajtów** przez dawną regułę „druga strona decyduje o szerokości”. Rozwiązanie: soczewka zawsze pisze swoją szerokość (sekcja 10, Z3).
2. **Pasek na widoku prostokątnym** nie daje się spłaszczyć do jednego widoku; rodzicem zostaje widok prostokątny (sekcja 14, wyjątek).
3. **`.size` i `.length`:** `.size` = rozmiar bloku, `.length` = długość tekstu.
