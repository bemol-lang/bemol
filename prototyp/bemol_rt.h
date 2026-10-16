/*
 * BEMOL ♭ — biblioteka wykonawcza prototypu (wersja 0)
 *
 * Menedżer bloków zgodny z bemol-wnetrze.md:
 *   - tablica wpisów po 32 bajty, numer wpisu = identyfikator bloku,
 *   - .shares + liczba widoków; blok zwalniany, gdy oba = 0,
 *   - widoki paskowe i prostokątne (podtabela prostokątów po 16 bajtów),
 *   - odczyt/zapis z odłamkami i kontrolą zakresu (.rangeError).
 *
 * Wersja 0 stawia na poprawność, nie na szybkość: optymalizacje
 * z rozdziału 9 dokumentu o wnętrzu nie są jeszcze zrobione.
 */
#ifndef BEMOL_RT_H
#define BEMOL_RT_H

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#ifdef _WIN32
#include <windows.h>
#endif

/* ------------------------------------------------------------------ */
/* Wpis menedżera bloków: 32 bajty                                      */
/* ------------------------------------------------------------------ */

typedef struct {
    uint64_t addr;    /* 0:  adres bloku (widok: przesunięcie w rodzicu)        */
    uint64_t size;    /* 8:  rozmiar bloku / długość widoku / pojemność tekstu  */
    uint32_t shares;  /* 16: liczba zmiennych trzymających blok                 */
    uint16_t flags;   /* 20: flagi serwisowe                                   */
    uint16_t views;   /* 22: liczba widoków patrzących na blok                 */
    uint64_t kind;    /* 24: pole zależne od rodzaju wpisu                     */
} bm_entry;

_Static_assert(sizeof(bm_entry) == 32, "wpis menedzera musi miec 32 bajty");

enum {
    BM_GLOBAL = 1 << 0,
    BM_PERSISTENT = 1 << 1,
    BM_VIEW = 1 << 2,
    BM_MAPPED = 1 << 3,
    BM_MAPPED_WRITABLE = 1 << 4,
    BM_TEXT = 1 << 5,
    BM_DEBUG_PATTERN = 1 << 6,
    BM_PRODUCTION_PATTERN = 1 << 7,
    BM_RANGE_SHIFT = 8,               /* bity 8–9: rangeError */
    BM_USED = 1 << 15                 /* prototyp: wpis zajęty (bit z puli wolnych) */
};

enum { RE_DEFAULT = 0, RE_CONTINUE = 1, RE_WARNING = 2, RE_HALT = 3 };

typedef struct {
    uint64_t rowbytes; /* bajty wiersza */
    uint64_t stride;   /* krok */
} bm_rect;

_Static_assert(sizeof(bm_rect) == 16, "opis prostokata musi miec 16 bajtow");

/* ------------------------------------------------------------------ */
/* Stan menedżera                                                       */
/* ------------------------------------------------------------------ */

static bm_entry *bm_T = NULL;
static uint32_t bm_cap = 0, bm_count = 1;      /* wpis 0 = „brak bloku” */
static uint32_t *bm_free = NULL;
static uint32_t bm_nfree = 0, bm_freecap = 0;

static bm_rect *bm_R = NULL;
static uint32_t bm_rcap = 0, bm_rcount = 1;    /* opis 0 = „brak prostokąta” */

static int bm_default_range = RE_HALT;

/* Start programu: konsola Windows w UTF-8, żeby polskie znaki wyświetlały się poprawnie. */
static void bm_start(void)
{
#ifdef _WIN32
    SetConsoleOutputCP(65001);
#endif
}
static const char *bm_srcfile = "?";

/* ------------------------------------------------------------------ */
/* Komunikaty błędów (format z sekcji 20 specyfikacji)                  */
/* ------------------------------------------------------------------ */

static void bm_message(int is_error, const char *code, int line, const char *msg, const char *detail, const char *help)
{
    fflush(stdout);
    const char *top = is_error
        ? "*****************************************************************"
        : "=================================================================";
    fprintf(stderr, "\n%s\n%s: %s\n%s\nat line %d\n", top, is_error ? "ERROR" : "WARNING", code, bm_srcfile, line);
    fprintf(stderr, "-----------------------------------------------------------------\n");
    fprintf(stderr, "  [ ! ] %s\n", msg);
    if (detail && *detail) fprintf(stderr, "  [ i ] %s\n", detail);
    if (help && *help) fprintf(stderr, "[ tip ] %s\n", help);
    fprintf(stderr, "_________________________________________________________________\n");
}

static void bm_fail(const char *code, int line, const char *msg, const char *detail, const char *help)
{
    bm_message(1, code, line, msg, detail, help);
    exit(70);
}

static void bm_warn(const char *code, int line, const char *msg, const char *detail)
{
    bm_message(0, code, line, msg, detail, "");
}

static bm_entry *bm_E(uint32_t id, int line)
{
    if (id == 0 || id >= bm_count || !(bm_T[id].flags & BM_USED))
        bm_fail("BML-E0001", line, "Zmienna nie wskazuje żadnego bloku",
                "zmienna `pointer` nie dostała jeszcze bloku przez .new albo przypisanie",
                "przydziel blok: zmienna.new[rozmiar]");
    return &bm_T[id];
}

static int bm_range_mode(uint32_t id)
{
    int m = (bm_T[id].flags >> BM_RANGE_SHIFT) & 3;
    return m == RE_DEFAULT ? bm_default_range : m;
}

/* Zwraca 1, gdy program ma kontynuować (CONTINUE/WARNING). */
static int bm_range_error(uint32_t id, int line, int write, uint64_t from, uint64_t n, uint64_t size)
{
    char det[256];
    snprintf(det, sizeof det, "blok #%u ma %llu B, %s bajtów %llu–%llu",
             id, (unsigned long long)size, write ? "zapis" : "odczyt",
             (unsigned long long)from, (unsigned long long)(from + n - 1));
    int m = bm_range_mode(id);
    if (m == RE_CONTINUE) return 1;
    if (m == RE_WARNING) { bm_warn("BML-W0100", line, write ? "Zapis poza blokiem" : "Odczyt poza blokiem", det); return 1; }
    bm_fail("BML-E0100", line, write ? "Zapis poza blokiem" : "Odczyt poza blokiem", det,
            "sprawdź indeks albo rozmiar bloku; tryb wyjścia poza blok ustawia .rangeError");
    return 0;
}

/* ------------------------------------------------------------------ */
/* Przydział wpisów                                                     */
/* ------------------------------------------------------------------ */

static uint32_t bm_alloc_entry(void)
{
    uint32_t id;
    if (bm_nfree) id = bm_free[--bm_nfree];
    else {
        if (bm_count >= bm_cap) {
            bm_cap = bm_cap ? bm_cap * 2 : 64;
            bm_T = realloc(bm_T, (size_t)bm_cap * sizeof(bm_entry));
            if (!bm_T) { fprintf(stderr, "brak pamięci na tablicę menedżera\n"); exit(71); }
        }
        id = bm_count++;
    }
    memset(&bm_T[id], 0, sizeof(bm_entry));
    bm_T[id].flags = BM_USED;
    return id;
}

static uint32_t bm_alloc_rect(uint64_t rowbytes, uint64_t stride)
{
    if (bm_rcount >= bm_rcap) {
        bm_rcap = bm_rcap ? bm_rcap * 2 : 16;
        bm_R = realloc(bm_R, (size_t)bm_rcap * sizeof(bm_rect));
    }
    bm_R[bm_rcount].rowbytes = rowbytes;
    bm_R[bm_rcount].stride = stride;
    return bm_rcount++;
}

static void bm_release_entry(uint32_t id)
{
    if (bm_nfree == bm_freecap) {
        bm_freecap = bm_freecap ? bm_freecap * 2 : 64;
        bm_free = realloc(bm_free, (size_t)bm_freecap * sizeof(uint32_t));
    }
    bm_T[id].flags = 0;
    bm_free[bm_nfree++] = id;
}

static uint32_t bm_parent(uint32_t id) { return (uint32_t)(bm_T[id].kind & 0xFFFFFFFFu); }
static uint32_t bm_rectid(uint32_t id) { return (uint32_t)(bm_T[id].kind >> 32); }

/* ------------------------------------------------------------------ */
/* Cykl życia: .new, .update, .release, shares                          */
/* ------------------------------------------------------------------ */

static void bm_new(uint32_t *var, uint64_t size, int line)
{
    if (*var != 0)
        bm_fail("BML-E0002", line, "Użyto .new drugi raz dla tej samej zmiennej",
                ".new rejestruje zmienną w menedżerze tylko raz w życiu zmiennej",
                "zmień rozmiar przez .update[rozmiar]");
    uint32_t id = bm_alloc_entry();
    bm_T[id].addr = (uint64_t)(uintptr_t)(size ? malloc(size) : NULL);
    if (size && !bm_T[id].addr) bm_fail("BML-E0003", line, "Brak pamięci", "", "");
    bm_T[id].size = size;
    bm_T[id].shares = 1;
    *var = id;
}

static void bm_update(uint32_t id, uint64_t size, int line)
{
    bm_entry *e = bm_E(id, line);
    if (e->flags & BM_VIEW)
        bm_fail("BML-E0004", line, "Użyto .update na widoku", "widok nie ma własnej pamięci", "zmień rozmiar bloku, na który patrzy widok");
    void *p = realloc((void *)(uintptr_t)e->addr, size ? size : 1);
    if (!p) bm_fail("BML-E0003", line, "Brak pamięci", "", "");
    e = &bm_T[id];
    e->addr = (uint64_t)(uintptr_t)p;
    e->size = size;
}

static void bm_free_storage(uint32_t id)
{
    bm_entry *e = &bm_T[id];
    if (e->flags & BM_VIEW) {
        uint32_t p = bm_parent(id);
        if (p && (bm_T[p].flags & BM_USED) && bm_T[p].views) bm_T[p].views--;
        e->kind = 0;
    } else if (e->addr) {
        free((void *)(uintptr_t)e->addr);
    }
    e->addr = 0;
    e->size = 0;
}

static void bm_drop(uint32_t id);

static void bm_maybe_free(uint32_t id)
{
    if (!(bm_T[id].flags & BM_USED)) return;
    if (bm_T[id].shares == 0 && bm_T[id].views == 0) {
        uint32_t parent = (bm_T[id].flags & BM_VIEW) ? bm_parent(id) : 0;
        bm_free_storage(id);
        bm_release_entry(id);
        if (parent) bm_maybe_free(parent);
    }
}

static void bm_retain(uint32_t id) { if (id) bm_T[id].shares++; }

static void bm_drop(uint32_t id)
{
    if (!id || id >= bm_count || !(bm_T[id].flags & BM_USED)) return;
    if (bm_T[id].shares) bm_T[id].shares--;
    bm_maybe_free(id);
}

static void bm_release(uint32_t id, int line)
{
    bm_entry *e = bm_E(id, line);
    if (e->views) {
        char det[128];
        snprintf(det, sizeof det, "blok #%u ma %u aktywn%s widok%s", id, e->views,
                 e->views == 1 ? "y" : "e", e->views == 1 ? "" : "i");
        bm_fail("BML-E0412", line, "Zwalniasz blok, na który patrzą widoki", det,
                "najpierw zwolnij widoki (.release), potem blok");
    }
    bm_free_storage(id);
}

/* Przypisanie wskaźnika: zmienna = inny blok */
static void bm_assign(uint32_t *var, uint32_t id)
{
    if (id) bm_retain(id);
    uint32_t old = *var;
    *var = id;
    if (old) bm_drop(old);
}

/* Przypisanie nowo utworzonego bloku (już ma shares = 1) */
static void bm_assign_new(uint32_t *var, uint32_t id)
{
    uint32_t old = *var;
    *var = id;
    if (old) bm_drop(old);
}

static uint64_t bm_size(uint32_t id, int line) { return id ? bm_E(id, line)->size : 0; }
static uint64_t bm_shares(uint32_t id, int line) { return bm_E(id, line)->shares; }

static void bm_set_range(uint32_t id, int mode, int line)
{
    bm_entry *e = bm_E(id, line);
    e->flags = (uint16_t)((e->flags & ~(3 << BM_RANGE_SHIFT)) | ((mode & 3) << BM_RANGE_SHIFT));
}

/* ------------------------------------------------------------------ */
/* Widoki                                                               */
/* ------------------------------------------------------------------ */

static uint32_t bm_view_portion(uint32_t parent, uint64_t off, uint64_t len, int line)
{
    bm_E(parent, line);
    uint64_t base = off;
    if ((bm_T[parent].flags & BM_VIEW) && !bm_rectid(parent)) {   /* spłaszczanie widoku widoku */
        base += bm_T[parent].addr;
        parent = bm_parent(parent);
    }
    /* pasek na widoku prostokątnym nie daje się spłaszczyć (może obejmować kilka wierszy):
       jego rodzicem zostaje widok prostokątny, a adres liczy się w dwóch krokach */
    uint32_t id = bm_alloc_entry();
    bm_entry *e = &bm_T[id];
    e->flags |= BM_VIEW | (bm_T[parent].flags & (3 << BM_RANGE_SHIFT));
    e->addr = base;
    e->size = len;
    e->shares = 1;
    e->kind = parent;
    bm_T[parent].views++;
    return id;
}

static uint32_t bm_view_rect(uint32_t parent, uint64_t x, uint64_t y, uint64_t w, uint64_t h, uint64_t stride, int line)
{
    bm_E(parent, line);
    if (bm_T[parent].flags & BM_VIEW)
        bm_fail("BML-E0900", line, "Widok prostokątny na widoku",
                "ta kombinacja nie jest jeszcze obsługiwana w prototypie (wersja 0)", "");
    uint32_t r = bm_alloc_rect(w, stride);
    uint32_t id = bm_alloc_entry();
    bm_entry *e = &bm_T[id];
    e->flags |= BM_VIEW | (bm_T[parent].flags & (3 << BM_RANGE_SHIFT));
    e->addr = y * stride + x;
    e->size = w * h;
    e->shares = 1;
    e->kind = (uint64_t)parent | ((uint64_t)r << 32);
    bm_T[parent].views++;
    return id;
}

/* Wskaźnik na bajt nr k bloku lub widoku; NULL = poza zakresem. */
static uint8_t *bm_byteptr(uint32_t id, uint64_t k);
static uint8_t *bm_byteptr(uint32_t id, uint64_t k)
{
    bm_entry *e = &bm_T[id];
    if (k >= e->size) return NULL;
    if (!(e->flags & BM_VIEW)) return (uint8_t *)(uintptr_t)e->addr + k;
    uint32_t p = bm_parent(id), r = bm_rectid(id);
    uint64_t pk;
    if (!r) pk = e->addr + k;
    else {
        uint64_t rb = bm_R[r].rowbytes;
        pk = e->addr + (k / rb) * bm_R[r].stride + (k % rb);
    }
    if (bm_T[p].flags & BM_VIEW) return bm_byteptr(p, pk);   /* rodzic też jest widokiem */
    if (pk >= bm_T[p].size) return NULL;
    return (uint8_t *)(uintptr_t)bm_T[p].addr + pk;
}

/* ------------------------------------------------------------------ */
/* Odczyt i zapis z odłamkami                                           */
/* ------------------------------------------------------------------ */

static void bm_read(uint32_t id, uint64_t off, void *dst, uint64_t n, int line)
{
    bm_entry *e = bm_E(id, line);
    uint8_t *d = (uint8_t *)dst;
    if (!(e->flags & BM_VIEW) && off + n <= e->size && off + n >= off) {   /* szybka ścieżka */
        memcpy(d, (uint8_t *)(uintptr_t)e->addr + off, n);
        return;
    }
    memset(d, 0, n);                                  /* odłamek: najpierw same zera */
    int reported = 0;
    for (uint64_t i = 0; i < n; i++) {
        uint8_t *p = bm_byteptr(id, off + i);
        if (p) d[i] = *p;
        else if (!reported) { reported = 1; bm_range_error(id, line, 0, off, n, e->size); }
    }
}

static void bm_write(uint32_t id, uint64_t off, const void *src, uint64_t n, int line)
{
    bm_entry *e = bm_E(id, line);
    const uint8_t *s = (const uint8_t *)src;
    if (!(e->flags & BM_VIEW) && off + n <= e->size && off + n >= off) {
        memcpy((uint8_t *)(uintptr_t)e->addr + off, s, n);
        return;
    }
    int reported = 0;
    for (uint64_t i = 0; i < n; i++) {
        uint8_t *p = bm_byteptr(id, off + i);
        if (p) *p = s[i];                              /* istniejące bajty */
        else if (!reported) { reported = 1; bm_range_error(id, line, 1, off, n, e->size); }
    }
}

/* Odczyt i zapis z dokładnością do bitu (do 64 bitów). */
static uint64_t bm_read_bits(uint32_t id, uint64_t bitoff, unsigned nbits, int line)
{
    uint64_t v = 0;
    for (unsigned i = 0; i < nbits; i++) {
        uint64_t b = bitoff + i;
        uint8_t byte = 0;
        bm_read(id, b / 8, &byte, 1, line);
        v |= (uint64_t)((byte >> (b % 8)) & 1) << i;
    }
    return v;
}

static void bm_write_bits(uint32_t id, uint64_t bitoff, unsigned nbits, uint64_t v, int line)
{
    for (unsigned i = 0; i < nbits; i++) {
        uint64_t b = bitoff + i;
        uint8_t *p = bm_byteptr(id, b / 8);
        if (!p) { bm_range_error(id, line, 1, b / 8, 1, bm_T[id].size); continue; }
        if ((v >> i) & 1) *p |= (uint8_t)(1u << (b % 8));
        else *p &= (uint8_t)~(1u << (b % 8));
    }
}

#define BM_RW(T, NAME)                                                                    \
    static T bm_rd_##NAME(uint32_t id, uint64_t off, int line)                            \
    { T v; bm_read(id, off, &v, sizeof(T), line); return v; }                             \
    static void bm_wr_##NAME(uint32_t id, uint64_t off, T v, int line)                    \
    { bm_write(id, off, &v, sizeof(T), line); }

BM_RW(uint8_t, u8)
BM_RW(uint16_t, u16)
BM_RW(uint32_t, u32)
BM_RW(uint64_t, u64)
BM_RW(int8_t, i8)
BM_RW(int16_t, i16)
BM_RW(int32_t, i32)
BM_RW(int64_t, i64)
BM_RW(float, f32)
BM_RW(double, f64)

/* ------------------------------------------------------------------ */
/* Operacje na całych blokach                                           */
/* ------------------------------------------------------------------ */

static void bm_fill(uint32_t id, const void *pattern, uint64_t plen, int line)
{
    bm_entry *e = bm_E(id, line);
    const uint8_t *s = (const uint8_t *)pattern;
    for (uint64_t k = 0; k < e->size; k++) {
        uint8_t *p = bm_byteptr(id, k);
        if (p) *p = s[k % plen];
    }
}

/* widok = widok: kopia danych, jak przez bufor (bezpieczna przy nachodzeniu) */
static void bm_copy_view(uint32_t dst, uint32_t src, int line)
{
    uint64_t n = bm_E(dst, line)->size;
    uint8_t *tmp = malloc(n ? n : 1);
    bm_read(src, 0, tmp, n, line);
    bm_write(dst, 0, tmp, n, line);
    free(tmp);
}

static uint32_t bm_copy_portion(uint32_t src, uint64_t off, uint64_t len, int line)
{
    uint32_t id = 0;
    bm_new(&id, len, line);
    uint8_t *d = (uint8_t *)(uintptr_t)bm_T[id].addr;
    bm_read(src, off, d, len, line);
    return id;
}

static uint32_t bm_copy_rect(uint32_t src, uint64_t x, uint64_t y, uint64_t w, uint64_t h, uint64_t stride, int line)
{
    uint32_t id = 0;
    bm_new(&id, w * h, line);
    uint8_t *d = (uint8_t *)(uintptr_t)bm_T[id].addr;
    for (uint64_t r = 0; r < h; r++) bm_read(src, y * stride + r * stride + x, d + r * w, w, line);
    return id;
}

static uint32_t bm_copy_all(uint32_t src, int line)
{
    return bm_copy_portion(src, 0, bm_E(src, line)->size, line);
}

/* ------------------------------------------------------------------ */
/* Wypisywanie                                                          */
/* ------------------------------------------------------------------ */

static void bm_print_str(const char *s) { fputs(s, stdout); }
static void bm_print_i(long long v) { printf("%lld", v); }
static void bm_print_u(unsigned long long v) { printf("%llu", v); }
static void bm_print_f(double v, int prec)
{
    if (prec >= 0) printf("%.*f", prec, v);
    else printf("%g", v);
}

static void bm_print_hex(unsigned long long v, int nbytes)
{
    printf("&");
    for (int i = nbytes - 1; i >= 0; i--) printf("%02llX", (v >> (i * 8)) & 0xFF);
    printf("h");
}

static void bm_print_bin(unsigned long long v, int nbits)
{
    printf("&");
    for (int i = nbits - 1; i >= 0; i--) putchar((v >> i) & 1 ? '1' : '0');
    printf("b");
}

/* Zrzut bloku: bajty w kolejności adresów, 16 w linii; widok prostokątny wiersz po wierszu. */
static void bm_dump(uint32_t id, int line)
{
    bm_entry *e = bm_E(id, line);
    uint64_t per = 16;
    if ((e->flags & BM_VIEW) && bm_rectid(id)) per = bm_R[bm_rectid(id)].rowbytes;
    printf("\n");
    for (uint64_t k = 0; k < e->size; k++) {
        if (k % per == 0) printf("%s%06llX:", k ? "\n" : "", (unsigned long long)k);
        uint8_t *p = bm_byteptr(id, k);
        if (p) printf(" %02X", *p); else printf(" --");
    }
}

static void bm_describe(uint32_t id, int line)
{
    if (!id) { printf("brak bloku"); return; }
    bm_entry *e = bm_E(id, line);
    if (e->flags & BM_VIEW)
        printf("widok #%u na bloku #%u, %llu B, shares %u", id, bm_parent(id),
               (unsigned long long)e->size, e->shares);
    else
        printf("blok #%u, %llu B, shares %u, widoki %u", id, (unsigned long long)e->size, e->shares, e->views);
}

/* ------------------------------------------------------------------ */
/* Zmienne struktur (na stosie): dostęp do pól bez wyrównania           */
/* ------------------------------------------------------------------ */

#define BM_LDST(T, NAME)                                                                  \
    static T bm_ld_##NAME(const void *p) { T v; memcpy(&v, p, sizeof(T)); return v; }     \
    static void bm_st_##NAME(void *p, T v) { memcpy(p, &v, sizeof(T)); }

BM_LDST(uint8_t, u8)
BM_LDST(uint16_t, u16)
BM_LDST(uint32_t, u32)
BM_LDST(uint64_t, u64)
BM_LDST(int8_t, i8)
BM_LDST(int16_t, i16)
BM_LDST(int32_t, i32)
BM_LDST(int64_t, i64)
BM_LDST(float, f32)
BM_LDST(double, f64)

/* ------------------------------------------------------------------ */
/* Rotacje i nasycenie                                                  */
/* ------------------------------------------------------------------ */

#define BM_ROT(T, NAME, BITS)                                                             \
    static T bm_rol_##NAME(T v, unsigned n) { n %= BITS; return n ? (T)((v << n) | (v >> (BITS - n))) : v; } \
    static T bm_ror_##NAME(T v, unsigned n) { n %= BITS; return n ? (T)((v >> n) | (v << (BITS - n))) : v; }

BM_ROT(uint8_t, u8, 8)
BM_ROT(uint16_t, u16, 16)
BM_ROT(uint32_t, u32, 32)
BM_ROT(uint64_t, u64, 64)

typedef __int128 bm_wide;

#define BM_SAT(T, NAME, LO, HI)                                                           \
    static T bm_sat_##NAME(bm_wide v) { return v < (bm_wide)(LO) ? (T)(LO) : v > (bm_wide)(HI) ? (T)(HI) : (T)v; }

BM_SAT(uint8_t, u8, 0, UINT8_MAX)
BM_SAT(uint16_t, u16, 0, UINT16_MAX)
BM_SAT(uint32_t, u32, 0, UINT32_MAX)
BM_SAT(uint64_t, u64, 0, UINT64_MAX)
BM_SAT(int8_t, i8, INT8_MIN, INT8_MAX)
BM_SAT(int16_t, i16, INT16_MIN, INT16_MAX)
BM_SAT(int32_t, i32, INT32_MIN, INT32_MAX)
BM_SAT(int64_t, i64, INT64_MIN, INT64_MAX)

#include <float.h>
static float bm_sat_f32(long double v) { return v < -FLT_MAX ? -FLT_MAX : v > FLT_MAX ? FLT_MAX : (float)v; }
static double bm_sat_f64(long double v) { return v < -DBL_MAX ? -DBL_MAX : v > DBL_MAX ? DBL_MAX : (double)v; }

/* ------------------------------------------------------------------ */
/* Teksty (wersja 0: literały, porównanie, dopisywanie, wypisywanie)    */
/* ------------------------------------------------------------------ */

static uint64_t bm_text_len(uint32_t id, int line)
{
    if (!id) return 0;
    bm_entry *e = bm_E(id, line);
    return (e->flags & BM_TEXT) ? e->kind : e->size;
}

static void bm_text_set(uint32_t *var, const char *s, uint64_t n, int line)
{
    if (*var == 0) {
        bm_new(var, n, line);
        bm_T[*var].flags |= BM_TEXT;
    } else if (bm_E(*var, line)->size < n) {
        bm_update(*var, n, line);                 /* rośnie dokładnie o tyle, ile trzeba */
    }
    memcpy((void *)(uintptr_t)bm_T[*var].addr, s, n);
    bm_T[*var].flags |= BM_TEXT;
    bm_T[*var].kind = n;
}

static void bm_text_append(uint32_t *var, const char *s, uint64_t n, int line)
{
    if (*var == 0) { bm_text_set(var, s, n, line); return; }
    uint64_t len = bm_text_len(*var, line), need = len + n;
    if (bm_T[*var].size < need) bm_update(*var, need, line);
    memcpy((uint8_t *)(uintptr_t)bm_T[*var].addr + len, s, n);
    bm_T[*var].kind = need;
}

static int bm_text_eq(uint32_t id, const char *s, uint64_t n, int line)
{
    if (bm_text_len(id, line) != n) return 0;     /* najpierw długości: natychmiast */
    return memcmp((void *)(uintptr_t)bm_T[id].addr, s, n) == 0;
}

static void bm_print_text(uint32_t id, int line)
{
    uint64_t n = bm_text_len(id, line);
    if (n) fwrite((void *)(uintptr_t)bm_T[id].addr, 1, n, stdout);
}

/* ------------------------------------------------------------------ */
/* Pętla for: jedno sprawdzenie zakresu przed pętlą                     */
/* ------------------------------------------------------------------ */

static void bm_for_check(int64_t a, int64_t b, int64_t step, int64_t lo, int64_t hi,
                         const char *var, const char *type, int line)
{
    char det[200];
    if (step == 0)
        bm_fail("BML-E0205", line, "Krok pętli for wynosi 0", "pętla nigdy by się nie skończyła", "podaj krok różny od 0");
    if (step > 0 ? a > b : a < b) return;             /* pętla nie wykona się ani razu */
    int64_t bad = (a < lo || a > hi) ? a : (b < lo || b > hi) ? b : 0;
    if (a < lo || a > hi || b < lo || b > hi) {
        snprintf(det, sizeof det, "licznik „%s” typu %s mieści %lld...%lld, a pętla doszłaby do %lld",
                 var, type, (long long)lo, (long long)hi, (long long)bad);
        bm_fail("BML-E0206", line, "Pętla for wychodzi poza zakres typu licznika", det,
                "wybierz szerszy typ licznika, np. as int");
    }
}

/* ------------------------------------------------------------------ */
/* keyInput: linia z klawiatury, bufor 255 bajtów                       */
/* ------------------------------------------------------------------ */

#define BM_KEYBUF 255
static char bm_keyline_buf[BM_KEYBUF + 2];

static uint64_t bm_keyline(int line)
{
    for (;;) {
        fflush(stdout);
        if (!fgets(bm_keyline_buf, sizeof bm_keyline_buf, stdin))
            bm_fail("BML-E0130", line, "Koniec danych wejściowych w keyInput",
                    "program czekał na linię z klawiatury, a wejście się skończyło", "");
        size_t n = strlen(bm_keyline_buf);
        int full = n && bm_keyline_buf[n - 1] == '\n';
        if (!full && !feof(stdin)) {                  /* linia dłuższa niż 255 bajtów */
            int ch;
            while ((ch = getchar()) != '\n' && ch != EOF) {}
            bm_print_str("[ ! ] Za długa linia (najwyżej 255 bajtów), wpisz jeszcze raz: ");
            continue;
        }
        while (n && (bm_keyline_buf[n - 1] == '\n' || bm_keyline_buf[n - 1] == '\r')) n--;
        bm_keyline_buf[n] = 0;
        return n;
    }
}

static const char *bm_key_trim(uint64_t *n)
{
    const char *s = bm_keyline_buf;
    while (*n && (*s == ' ' || *s == '\t')) { s++; (*n)--; }
    while (*n && (s[*n - 1] == ' ' || s[*n - 1] == '\t')) (*n)--;
    return s;
}

static int bm_key_int(uint64_t n, int64_t lo, int64_t hi, int64_t *out)
{
    const char *s = bm_key_trim(&n);
    if (!n) return 0;
    char tmp[BM_KEYBUF + 1], *end;
    memcpy(tmp, s, n); tmp[n] = 0;
    errno = 0;
    long long v = strtoll(tmp, &end, 10);
    if (*end || errno || v < lo || v > hi) return 0;
    *out = v;
    return 1;
}

static int bm_key_uint(uint64_t n, uint64_t hi, uint64_t *out)
{
    const char *s = bm_key_trim(&n);
    if (!n || *s == '-') return 0;
    char tmp[BM_KEYBUF + 1], *end;
    memcpy(tmp, s, n); tmp[n] = 0;
    errno = 0;
    unsigned long long v = strtoull(tmp, &end, 10);
    if (*end || errno || v > hi) return 0;
    *out = v;
    return 1;
}

static int bm_key_float(uint64_t n, double *out)
{
    const char *s = bm_key_trim(&n);
    if (!n) return 0;
    char tmp[BM_KEYBUF + 1], *end;
    memcpy(tmp, s, n); tmp[n] = 0;
    for (char *p = tmp; *p; p++) if (*p == ',') *p = '.';   /* przecinek też jest dobry */
    double v = strtod(tmp, &end);
    if (*end) return 0;
    *out = v;
    return 1;
}

static void bm_key_bad(const char *what)
{
    printf("[ ! ] To nie jest %s, wpisz jeszcze raz\n", what);
}

/* ------------------------------------------------------------------ */
/* INPUT.read[bufor]: kolejne bajty wejścia, wynik = ile przeczytano    */
/* ------------------------------------------------------------------ */

static int64_t bm_input_read(uint32_t id, int line)
{
    bm_entry *e = bm_E(id, line);
    uint64_t cap = e->size;
    if (!cap) return 0;
    fflush(stdout);
    if (!(e->flags & BM_VIEW)) {
        size_t got = fread((void *)(uintptr_t)e->addr, 1, cap, stdin);
        if (e->flags & BM_TEXT) e->kind = got;
        return (int64_t)got;
    }
    uint8_t *tmp = (uint8_t *)malloc(cap);
    if (!tmp) bm_fail("BML-E0003", line, "Brak pamięci", "", "");
    size_t got = fread(tmp, 1, cap, stdin);
    bm_write(id, 0, tmp, got, line);
    free(tmp);
    return (int64_t)got;
}

#endif /* BEMOL_RT_H */
