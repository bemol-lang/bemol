# BEMOL ♭ — prototyp tłumacza (wersja 0.2)

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

Wszystkie opcje:

```
python3 bemolc.py program.bmol             # kompilacja testowa → program (.exe na Windows)
python3 bemolc.py -finalbake program.bmol  # finalbake (pełna optymalizacja kompilatora C)
python3 bemolc.py --emit-c program.bmol    # tylko wygenerowany kod C (program.c)
python3 bemolc.py --debug program.bmol     # pełny ślad Pythona przy błędzie wewnętrznym tłumacza
```

Tłumacz nigdy nie powinien kończyć się surowym śladem Pythona. Jeśli tak się stanie, to błąd prototypu: zgłoś go razem z plikiem `.bmol`.

## Pliki

| Plik | Zawartość |
|---|---|
| `bemolc.py` | tłumacz: lekser, parser, generator kodu C, komunikaty błędów |
| `bemol_rt.h` | biblioteka wykonawcza: menedżer bloków (wpisy 32 B), widoki, odczyt/zapis z odłamkami, `.rangeError`, wypisywanie |
| `przyklady/widok10x10.bmol` | przykład 10 × 10 z `bemol-wnetrze.md`, rozdział 5 |
| `przyklady/tekstura.bmol` | obraz 256 × 256 pikseli `Color`: widoki, kopie, `foreach`, `saturate`, funkcje |
| `przyklady/petle.bmol` | typowane liczniki `for`, licznik zadeklarowany przed pętlą, zamiana `as` |
| `przyklady/menu.bmol` | interaktywne menu z `keyInput`: tekst i liczby z klawiatury, `.update`, `.fill`, zrzut |
| `przyklady/wejscie.bmol` | `INPUT.read[bufor]`: czytanie wejścia porcjami (`wejscie < plik.txt`) |
| `przyklady/blad_*.bmol` | przykłady komunikatów błędów |

## Co obsługuje wersja 0

- **typy:** `byte`, `unsigned_8/16/32/64`, `signed_8`, `shortint`, `int`, `longint`, `float`, `doublefloat`, `bit`, `pointer`, `text`,
- **deklaracje:** zmienne, `GLOBAL`, `CONST`, `STRUCT` (pola o pełnych bajtach), `ALIAS`,
- **bloki:** `.new`, `.update`, `.release`, `.clear`, `.fill`, `.size`, `.shares`, `.rangeError`,
- **soczewki:** `ptr.<typ>[n]`, pola struktur `ptr.Color[n].G`, reguła szerokości z sekcji 10 (typ zmiennej po drugiej stronie, literały szesnastkowe i binarne bit po bicie),
- **operacje blokowe:** `ptr.byte += 1`, `ptr.float = 1.5`, `ptr.byte = saturate(ptr.byte + 60)`, także `xor=`, `shl=` itd.,
- **widoki i kopie:** `viewPortion`, `viewRectangle`, `copy`, `copyPortion`, `copyRectangle`, przypisanie widoku do widoku (kopia danych),
- **liczniki:** `.shares` i liczba widoków, zwalnianie bloku na końcu zasięgu, zakaz `.release` bloku z aktywnymi widokami,
- **sterowanie:** `if`/`elseif`/`else`, `while`, `repeat...until`, `break`, `continue`, separator `;`,
- **`for` z typowanym licznikiem:** `for i as int = 0 to 99 [step s] do` (nowa zmienna pętli, znika po `for.end`) albo `for i = ...` dla zmiennej zadeklarowanej wcześniej (zostaje w niej ostatnia wartość); wewnętrzny licznik 64-bitowy, zakres sprawdzany raz przed pętlą (dla literałów już przy kompilacji), krok 0 to błąd,
- **`foreach px, nr as int in blok.T`** (numer elementu z jawnym typem),
- **zamiana `as`:** `wartosc as byte` (najmłodsza część), `x as int` (ułamek odcięty), `as bit`; wiąże mocniej niż `+` i `*`, a w regule szerokości liczy się jak zmienna danego typu: `blok.byte[i] = i as byte` zapisuje 1 B,
- **wejście:** `keyInput("tekst", REF zmienna, ...)` (linia do 255 B, sprawdzanie typu i zakresu z ponowieniem, tekst dostaje dokładnie tyle bajtów, ile wpisano; `keyInput()` czeka na Enter), `n = INPUT.read[bufor]` (zwraca liczbę przeczytanych bajtów, 0 = koniec danych),
- **funkcje:** parametry kopiowane, bloki przez wskaźnik, `CONST`, `REF` (także przy wywołaniu), `return`, `: void`,
- **teksty:** `t as text = "..."`, `.length`, `.size`, `.append[...]`, porównanie `==` treści,
- **wypisywanie:** `print`, `println`, formaty `: hex`, `: bin`, `: N`, zrzut bloku `println(blok : hex)`,
- **`BUILD_MODE`**, `return` z kodem zakończenia w `MAIN`, `saturate( )`, `rol`/`ror`.

## Czego jeszcze nie ma

`switch`, `ENUM`, klasy, `PERSISTENT`, `.map`, `.value` (cały blok jako liczba), typy o nietypowej szerokości (`unsigned_12`) i pola bitowe w strukturach, `halffloat`, wzory pamięci, `@ACCEPT` (jest pomijane), zwracanie kilku wartości, `ARGS`, praca równoległa.
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

**Komunikaty błędów** (format z sekcji 20 specyfikacji):

```
*****************************************************************
ERROR: BML-E0300
blad_licznik.bmol
at line 7, column 5
-----------------------------------------------------------------
7 |     println("ostatnie i = ", i)
  |     ^
-----------------------------------------------------------------
  [ ! ] Nieznana nazwa „i”
  [ i ] „i” istniało tylko w pętli for z linii 4 i zniknęło po for.end
[ tip ] jeśli wartość jest potrzebna po pętli, zadeklaruj „i as int” przed pętlą i pisz: for i = ...
_________________________________________________________________
```

Błędy w czasie działania programu (np. BML-E0412, BML-E0206) mają tę samą ramkę, bez linii kodu.

## Odkrycia z prototypu (do decyzji w specyfikacji)

1. ~~**`blok.byte[i] = i` zapisuje 8 bajtów.**~~ **Rozwiązane:** licznik pętli ma teraz jawny typ (`for i as int = ...`), a zamianę zapisuje się `blok.byte[i] = i as byte`.
2. **Pasek na widoku prostokątnym** (`kafelek.viewPortion[0:20]`) nie daje się spłaszczyć do jednego widoku, bo może obejmować kilka wierszy. Prototyp trzyma wtedy widok prostokątny jako rodzica i liczy adres w dwóch krokach. Specyfikacja zakłada zawsze jeden poziom.
3. **`.size` i `.length`:** `.size` = rozmiar bloku, `.length` = długość tekstu (już w specyfikacji).
