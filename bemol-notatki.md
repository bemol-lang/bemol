# BEMOL — notatki do późniejszej analizy

Przemyślenia Tomasza zapisane do omówienia później.

## 2026-10-17

1. **Kompilator BEMOL-a napisany w BEMOL-u.** Czego brakuje w samym języku („hydraulice”), żeby dało się w nim napisać pełnoprawny kompilator?
   - *Analiza:* jest wczytanie pliku (`.map`), dostęp do znaków (`.byte`), rekurencja, `STRUCT`, rosnące bloki, `switch`/`ENUM`. Brakuje: zapisu pliku, zamiany liczba ↔ tekst, programów z wielu plików, uruchamiania innego programu (albo generowania `.exe`). Drzewo składni (AST): zalecane węzły jako elementy jednego dużego bloku `STRUCT`, dzieci wskazywane numerem elementu (działa już dziś). Alternatywa: pełnoprawne odwołania do bloków w polach struktur (nowa decyzja).

2. **Biblioteki narzędzi do obsługi bloków.** Teraz bloki mają tylko natywne operatory wbudowane w język (i to dobrze). Czy warto dodatkowo obudować działania na blokach w klasę z metodami, dla czytelności i łatwości obsługi?
   - *Analiza:* nie osobna klasa opakowująca blok (dwa sposoby zapisu tej samej czynności), tylko biblioteka dopisująca nowe metody do samego bloku (*extension methods*): `dane.find[&FFD8h]`, `dane.byte.sum`, `dane.saveAs["wynik.raw"]`. Metody wbudowane i biblioteczne wyglądają tak samo. Wyżej: klasy do konkretnych zadań (`Obraz`, `Czytnik`, `Lista`), które wymagają bloku jako pola klasy (ta sama decyzja co odwołania do bloków w punkcie 1).
   - Sprawdzić w praktyce, czy początkujący posługuje się językiem bez głupich błędów. Każda pomyłka Tomasza = „pułapka” do zapisania tutaj, a potem błąd lub ostrzeżenie kompilatora z podpowiedzią.

3. **Przekazywanie bloków do funkcji i `REF`.** Założenie Tomasza: żeby funkcja zmieniła blok bez kopiowania, trzeba pisać `FUNCTION Przelicz(REF blok)`, bo `return` zwróciłby nową, zmienioną kopię. Pytanie: czy kompilator zgłasza błąd, gdy programista nie napisze `REF` przy wywołaniu?
   - *Analiza:* bloki nie są kopiowane ani przy przekazaniu, ani przy `return` (przekazywany jest numer bloku). Jeśli deklaracja ma `REF`, wywołanie też musi go mieć (prototyp: błąd BML-E0353).
   - `REF` przy wskaźniku nie jest przezroczysty: bez `REF` funkcja zmienia dane bloku, ale podmiana bloku (`dane = innyBlok`, `.new`, `.release`) działa tylko lokalnie; z `REF` podmienia blok wywołującego.
   - **Wykryta niespójność:** `rozjasnij(foto)` zmienia dane `foto`, a w miejscu wywołania tego nie widać — ta sama pułapka co w C++, przed którą miało chronić `REF`. Ramka „Dlaczego `REF` także przy wywołaniu?” w specyfikacji obiecuje więcej, niż dają obecne zasady.
   - **DECYZJA (wpisana do specyfikacji, sekcja 3):** trzy poziomy uprawnień: `CONST` = tylko odczyt; bez znacznika = zmiana danych i `.update`, ale bez `.release`, `.new` i podmiany; `REF` = także podmiana i `.release` (skutki dla `.shares`). Ramka o `REF` poprawiona: w wywołaniu widać zmianę samej zmiennej, nie danych bloku.

## Przyjęte do specyfikacji (2026-10-17, wpisane do specyfikacji)

- **Deklaracja z przydziałem bloku:** `blok as pointer.new[1024]` = skrót dwóch linii (`blok as pointer` + `blok.new[1024]`), tylko w deklaracji, tak jak `x as int = 5` dla liczb. Działa jak `.new`: rejestruje zmienną, przydziela blok, nie zeruje.
- **Bez `: void`:** funkcja bez `:` po nawiasie nic nie zwraca. `return wartość` w takiej funkcji = błąd kompilacji; samo `return` (wyjście) dozwolone.

## Pułapki (pomyłki do zamiany na czytelne błędy kompilatora)

- **Niepasujące zamknięcie funkcji** (`zmienREF.end` zamyka funkcję `zmien`, po skopiowaniu kodu): błąd z podpowiedzią poprawnej nazwy.
- **Literał bez znacznika systemu** (`&FF` zamiast `&FFh`): błąd z podpowiedzią `&FFh` / `&...b`.

## Do zrobienia w prototypie

- Uprawnienia do bloku w funkcji: bez znacznika = zapis danych; `.new`/`.update`/`.release`/`.append`/podmiana tylko z `REF` (dziś prototyp przyjmuje `REF` tylko dla zmiennych statycznych); błąd z podpowiedzią „dodaj `REF`”.
- `CONST` obowiązujący do końca funkcji: blok `CONST` tylko do parametrów `CONST`, widoki z bloku `CONST` też `CONST`.
- Błąd: ten sam blok w dwóch parametrach, z których choć jeden może zmieniać blok.
- Cecha funkcji „zmienia bloki globalne” (potrzebna dopiero przy optymalizacjach z wnętrza, rozdział 9).
- **Zasady Z1–Z5** (prototyp liczy jeszcze po staremu): stół 64-bitowy (`longint`/`doublefloat`) i dopasowanie przy zapisie; soczewka zawsze w swojej szerokości (usunąć regułę „druga strona” i W0110); `.at[n]`; literał dziesiętny bez soczewki w `.fill` = błąd; przykłady i README.
- Funkcje bez `: void`.
- `blok as pointer.new[1024]`.
- Błąd przy niepasującym zamknięciu funkcji i przy literale bez `h`/`b`.

## Otwarte drobiazgi

- `INPUT.read[bufor]` dla bloku `text` ustawia długość tekstu (pole wpisu w menedżerze). Czy według nowej zasady wymaga `REF bufor`? Dla `pointer` nie zmienia wpisu, więc `REF` niepotrzebne.

## Przegląd specyfikacji pod kątem pułapek (2026-10-17)

### Poważne (pułapki dla programisty)

1. **[ROZWIĄZANE: zasady Z3–Z5 wpisane do sekcji 10]** **Reguła szerokości przy odczycie (sekcja 10).** `x as int = dane.byte[5]` czyta 4 bajty, `if dane.byte[k] == licznik` czyta 4 bajty, a `suma = ptr.byte[5] + ptr.byte[6]` czyta po 1 bajcie — dopisanie `+ 0` zmienia wynik. Propozycja: soczewka zawsze czyta i zapisuje swoją szerokość; szersza wartość przy zapisie = błąd z podpowiedzią `as`; dostęp do dowolnego typu od dowolnego bajtu jawnie, np. `ptr.doublefloat.at[1009]` (pozycja w bajtach).
2. **[ROZWIĄZANE: zasady Z1–Z2 wpisane do sekcji 5]** **Obliczenia w typie docelowym / najszerszym składników (sekcja 5).** `srednia as byte = (a + b) / 2` przy 200 i 200 daje 72 zamiast 200; `if a + b > 255` (bajty) nigdy nie jest prawdziwe; `wynik as int = 7.9 + 0.5` daje 7 (składniki zamieniane na int przed dodaniem). Propozycja: obliczenia pośrednie w szerokim typie (`longint` / `doublefloat`), zawijanie dopiero przy zapisie; kompilator zawęża tam, gdzie wynik jest identyczny (+, −, *, and, or, xor, shl), więc SIMD na bajtach zostaje.
3. **Przypisanie tekstów (sekcje 7 i 18).** `t = "abc"` kopiuje treść, a reguła z sekcji 7 mówi „sama zmienna po lewej = przypisanie wskaźnika”; „literał tylko do odczytu, zmiana przez `t = "abc".copy`” przeczy przykładowi `t = "abc"`; `a = b` dla dwóch tekstów niejasne (jeśli wskaźnik, `a.append` zmienia też `b`). Propozycja: dla `text` przypisanie `=` zawsze kopiuje treść.

### Spójność

4. **Klasa na stosie a w bloku (sekcja 25).** Pole `pointer` w obiekcie na stosie liczy się do `.shares`, w obiekcie w bloku jest zwykłą liczbą: ta sama klasa zachowuje się różnie. Kopiowanie struktury z polem `pointer` (parametr, `=`) to ukryta operacja na `.shares`, wbrew zasadzie „bez ukrytych operacji”. Wiąże się z decyzją „bloki wskazujące bloki”.
5. **[ROZWIĄZANE: „Trzy cele BEMOL-a” i nowe brzmienie zasady w sekcji 1]** **Filozofia (sekcja 1):** „Język mu niczego nie zabrania” przeczy wielu zakazom (`=` w warunku, float w `for`, przesłanianie, `REF`). Przeformułować: język nie zabrania dostępu do danych, zabrania niejednoznacznego zapisu.
6. **Trzy składnie deklaracji typów:** `Color as STRUCT { ... }`, `ENUM Stan { ... }`, `CLASS X ... X.end`.
7. **`ENUM` bez jawnego typu** zmienia szerokość po dodaniu wartości, więc w `STRUCT` (np. nagłówek pliku) po cichu zmienia się układ danych. Propozycja: w `STRUCT` tylko `ENUM` z jawnym typem.

### Drobne

8. `.release` bloku z widokami w finalbake „według `DEFAULT_RANGE_ERROR`”: co znaczy wtedy `CONTINUE`? (wiąże się z `@ACCEPT RUNTIME_ERROR`).
9. Ustawienia programu (`DEFAULT_RANGE_ERROR = ...`, `DEFAULT_MEMORY_PATTERN_DEBUG = ON`) bez opisanej składni i miejsca w pliku; `ON`/`OFF`, `true`/`false`, `WRITABLE`, `INPUT`, `keyInput` nie występują w spisie słów w sekcji 3.
10. `mn, mx = minmax(...)`: nie wiadomo, czy `mn` i `mx` muszą być wcześniej zadeklarowane.
