/* Wygenerowane przez bemolc (prototyp, wersja 0) — nie edytować ręcznie */
#define BEMOL_BUILD_MODE 0
#include "bemol_rt.h"




int main(int argc, char **argv)
{
    (void)argc; (void)argv;
    bm_start();
    bm_srcfile = "menu.bmol";
    uint32_t v_imie = 0;
    for (;;) {
        bm_print_str("Jak masz na imi\304\231? ");
        uint64_t _kn = bm_keyline(5);
        bm_text_set(&v_imie, bm_keyline_buf, _kn, 5); break;
    }
    bm_print_str("Cze\305\233\304\207, ");
    bm_print_text(v_imie, 6);
    bm_print_str("! (");
    bm_print_i((long long)((int64_t)bm_text_len(v_imie, 6)));
    bm_print_str(" B)");
    bm_print_str("\n");
    uint32_t v_dane = 0;
    bm_new(&v_dane, 8LL, 9);
    uint8_t v_wybor = ((uint8_t)(0LL));
    do {
        bm_print_str("");
        bm_print_str("\n");
        bm_print_str("1 - zmie\305\204 rozmiar bloku   2 - wype\305\202nij bajtem   3 - poka\305\274 blok   0 - koniec");
        bm_print_str("\n");
        for (;;) {
            bm_print_str("Wyb\303\263r: ");
            uint64_t _kn = bm_keyline(15);
            uint64_t _kv; if (bm_key_uint(_kn, 255ULL, &_kv)) { v_wybor = (uint8_t)_kv; break; }
            bm_key_bad("liczba typu byte (0...255)");
        }
        if (((int64_t)(v_wybor) == (int64_t)(1LL))) {
            uint32_t v_rozmiar = 0;
            for (;;) {
                bm_print_str("Nowy rozmiar w bajtach: ");
                uint64_t _kn = bm_keyline(18);
                uint64_t _kv; if (bm_key_uint(_kn, 4294967295ULL, &_kv)) { v_rozmiar = (uint32_t)_kv; break; }
                bm_key_bad("liczba typu unsigned_32 (0...4294967295)");
            }
            bm_update(v_dane, v_rozmiar, 19);
            bm_print_str("Blok ma teraz ");
            bm_print_i((long long)(bm_size(v_dane, 20)));
            bm_print_str(" B");
            bm_print_str("\n");
        } else if (((int64_t)(v_wybor) == (int64_t)(2LL))) {
            uint8_t v_wartosc = 0;
            for (;;) {
                bm_print_str("Bajt (0...255): ");
                uint64_t _kn = bm_keyline(23);
                uint64_t _kv; if (bm_key_uint(_kn, 255ULL, &_kv)) { v_wartosc = (uint8_t)_kv; break; }
                bm_key_bad("liczba typu byte (0...255)");
            }
            { uint8_t _p1 = ((uint8_t)(v_wartosc)); bm_fill(v_dane, &_p1, sizeof _p1, 24); }
        } else if (((int64_t)(v_wybor) == (int64_t)(3LL))) {
            bm_print_str("Rozmiar bloku: ");
            bm_print_i((long long)(bm_size(v_dane, 26)));
            bm_print_str(" B ");
            bm_print_str("\n");
            bm_dump(v_dane, 27);
            bm_print_str("\n");
        } else if (((int64_t)(v_wybor) != (int64_t)(0LL))) {
            bm_print_str("Nie ma takiej opcji");
            bm_print_str("\n");
        }
    } while (!(((int64_t)(v_wybor) == (int64_t)(0LL))));
    bm_print_str("Naci\305\233nij Enter, aby zako\305\204czy\304\207...");
    bm_keyline(33);
    bm_drop(v_dane);
    bm_drop(v_imie);
    return 0;
}
