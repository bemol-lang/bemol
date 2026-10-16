/* Wygenerowane przez bemolc (prototyp, wersja 0) — nie edytować ręcznie */
#define BEMOL_BUILD_MODE 0
#include "bemol_rt.h"

static const int32_t c_SZER = ((int32_t)256LL);
static const int32_t c_WYS = ((int32_t)256LL);
static uint32_t g_obraz = 0;

static double f_sumaR(uint32_t v_dane);
static void f_zamien(int32_t *v_a, int32_t *v_b);

static double f_sumaR(uint32_t v_dane)
{
    double v_s = ((double)0LL);
    { uint32_t _fb1 = v_dane; uint64_t _fn2 = bm_size(_fb1, 80) / 10;
    for (uint64_t _fi3 = 0; _fi3 < _fn2; _fi3++) {
        v_s = ((double)((double)(v_s) + (double)(bm_rd_u16(_fb1, ((_fi3 * 10) + 0), 81))));
    }}
    { double _rv = v_s;
    return _rv; }
    return (double)0;
}

static void f_zamien(int32_t *v_a, int32_t *v_b)
{
    int32_t v_t = (*v_a);
    (*v_a) = (*v_b);
    (*v_b) = v_t;
}


int main(int argc, char **argv)
{
    (void)argc; (void)argv;
    bm_srcfile = "tekstura.bmol";
    bm_new(&g_obraz, ((int64_t)((int64_t)(((int64_t)((int64_t)(c_SZER) * (int64_t)(c_WYS)))) * (int64_t)(10))), 13);
    bm_print_str("Obraz: ");
    bm_describe(g_obraz, 14);
    bm_print_str("  (oczekiwane 655360 B = 256 \303\227 256 \303\227 10)");
    bm_print_str("\n");
    { int64_t _end4 = ((int64_t)((int64_t)(c_WYS) - (int64_t)(((int64_t)1LL))));
    for (int64_t v_y = ((int64_t)0LL); v_y <= _end4; v_y++) {
        { int64_t _end5 = ((int64_t)((int64_t)(c_SZER) - (int64_t)(((int64_t)1LL))));
        for (int64_t v_x = ((int64_t)0LL); v_x <= _end5; v_x++) {
            int64_t v_n = ((int64_t)((int64_t)(((int64_t)((int64_t)(v_y) * (int64_t)(c_SZER)))) + (int64_t)(v_x)));
            uint16_t v_r = ((uint16_t)((uint16_t)(v_x) * (uint16_t)(((uint16_t)256LL))));
            uint16_t v_g = ((uint16_t)((uint16_t)(v_y) * (uint16_t)(((uint16_t)256LL))));
            bm_wr_u16(g_obraz, (((v_n) * 10) + 0), v_r, 22);
            bm_wr_u16(g_obraz, (((v_n) * 10) + 2), v_g, 23);
            bm_wr_u16(g_obraz, (((v_n) * 10) + 4), ((uint16_t)1000LL), 24);
            bm_wr_u32(g_obraz, (((v_n) * 10) + 6), ((uint32_t)65535LL), 25);
        }}
    }}
    bm_print_str("Piksel (100, 50): R = ");
    bm_print_u((unsigned long long)(bm_rd_u16(g_obraz, (((((int64_t)((int64_t)(((int64_t)((int64_t)(((int64_t)50LL)) * (int64_t)(c_SZER)))) + (int64_t)(((int64_t)100LL))))) * 10) + 0), 29)));
    bm_print_str(", G = ");
    bm_print_u((unsigned long long)(bm_rd_u16(g_obraz, (((((int64_t)((int64_t)(((int64_t)((int64_t)(((int64_t)50LL)) * (int64_t)(c_SZER)))) + (int64_t)(((int64_t)100LL))))) * 10) + 2), 30)));
    bm_print_str("   (oczekiwane 25600, 12800)");
    bm_print_str("\n");
    uint32_t v_kafelek = 0;
    uint32_t _t6 = bm_view_rect(g_obraz, ((int64_t)((int64_t)(((int64_t)100LL)) * (int64_t)(10))), ((int64_t)50LL), ((int64_t)((int64_t)(((int64_t)4LL)) * (int64_t)(10))), ((int64_t)2LL), ((int64_t)((int64_t)(c_SZER) * (int64_t)(10))), 33);
    bm_assign_new(&v_kafelek, _t6);
    bm_print_str("Kafelek: ");
    bm_describe(v_kafelek, 34);
    bm_print_str("  (oczekiwane 80 B = 4 \303\227 2 \303\227 10)");
    bm_print_str("\n");
    bm_print_str("Kafelek, pierwszy wiersz (R = 25600 = &6400h):");
    uint32_t _t7 = bm_view_portion(v_kafelek, ((int64_t)0LL), ((int64_t)20LL), 35);
    bm_dump(_t7, 35);
    bm_print_str("\n");
    bm_drop(_t7);
    uint32_t v_miniatura = 0;
    uint32_t _t8 = bm_copy_rect(g_obraz, ((int64_t)((int64_t)(((int64_t)100LL)) * (int64_t)(10))), ((int64_t)50LL), ((int64_t)((int64_t)(((int64_t)4LL)) * (int64_t)(10))), ((int64_t)2LL), ((int64_t)((int64_t)(c_SZER) * (int64_t)(10))), 38);
    bm_assign_new(&v_miniatura, _t8);
    { uint32_t _fb9 = v_kafelek; uint64_t _fn10 = bm_size(_fb9, 41) / 10;
    for (uint64_t _fi11 = 0; _fi11 < _fn10; _fi11++) {
        bm_wr_u16(_fb9, ((_fi11 * 10) + 0), ((uint16_t)((uint16_t)(((uint16_t)65535LL)) - (uint16_t)(bm_rd_u16(_fb9, ((_fi11 * 10) + 0), 42)))), 42);
    }}
    bm_print_str("Po odwr\303\263ceniu R w kafelku: obraz (100, 50).R = ");
    bm_print_u((unsigned long long)(bm_rd_u16(g_obraz, (((((int64_t)((int64_t)(((int64_t)((int64_t)(((int64_t)50LL)) * (int64_t)(c_SZER)))) + (int64_t)(((int64_t)100LL))))) * 10) + 0), 44)));
    bm_print_str("   (oczekiwane 39935)");
    bm_print_str("\n");
    bm_print_str("Kopia nietkni\304\231ta:         miniatura[0].R = ");
    bm_print_u((unsigned long long)(bm_rd_u16(v_miniatura, (((((int64_t)0LL)) * 10) + 0), 46)));
    bm_print_str("   (oczekiwane 25600)");
    bm_print_str("\n");
    uint32_t v_jasny = 0;
    uint32_t _t12 = bm_copy_all(v_miniatura, 50);
    bm_assign_new(&v_jasny, _t12);
    { uint32_t _blk14 = v_jasny;
      uint64_t _n15 = (bm_size(_blk14, 51) + 0) / 1;
      for (uint64_t _i13 = 0; _i13 < _n15; _i13++) {
        bm_wr_u8(_blk14, (_i13 * 1), bm_sat_u8(((bm_wide)((bm_wide)(bm_rd_u8(v_jasny, (_i13 * 1), 51)) + (bm_wide)(((bm_wide)200LL))))), 51);
      }
    }
    bm_print_str("Bajty miniatury przed: ");
    { int64_t _end16 = ((int64_t)9LL);
    for (int64_t v_k = ((int64_t)0LL); v_k <= _end16; v_k++) {
        bm_print_u((unsigned long long)(bm_rd_u8(v_miniatura, ((v_k) * 1), 53)));
        bm_print_str(" ");
    }}
    bm_print_str("");
    bm_print_str("\n");
    bm_print_str("Bajty po saturate(+200): ");
    { int64_t _end17 = ((int64_t)9LL);
    for (int64_t v_k = ((int64_t)0LL); v_k <= _end17; v_k++) {
        bm_print_u((unsigned long long)(bm_rd_u8(v_jasny, ((v_k) * 1), 56)));
        bm_print_str(" ");
    }}
    bm_print_str("   (ka\305\274dy \342\211\244 255, bez \342\200\236przekr\304\231cenia\342\200\235)");
    bm_print_str("\n");
    double v_suma = f_sumaR(v_kafelek);
    bm_print_str("Suma R w kafelku: ");
    bm_print_f((double)(v_suma), 0);
    bm_print_str("   (oczekiwane 316408 = 2 \303\227 (4 \303\227 65535 \342\210\222 256 \303\227 (100+101+102+103)))");
    bm_print_str("\n");
    int32_t v_a = ((int32_t)3LL);
    int32_t v_b = ((int32_t)7LL);
    f_zamien(&v_a, &v_b);
    bm_print_str("Po zamien(REF a, REF b): a = ");
    bm_print_i((long long)(v_a));
    bm_print_str(", b = ");
    bm_print_i((long long)(v_b));
    bm_print_str("\n");
    uint16_t v_v = bm_rd_u16(g_obraz, (((((int64_t)0LL)) * 10) + 6), 68);
    bm_print_str("Alpha = ");
    bm_print_hex((unsigned long long)(v_v), 2);
    bm_print_str(" = ");
    bm_print_bin((unsigned long long)(v_v), 16);
    bm_print_str("\n");
    bm_release(v_kafelek, 71);
    bm_release(v_jasny, 72);
    bm_release(v_miniatura, 73);
    bm_release(g_obraz, 74);
    { int _rc = (int)(((int32_t)0LL));
    bm_drop(v_jasny);
    bm_drop(v_miniatura);
    bm_drop(v_kafelek);
    return _rc; }
    bm_drop(v_jasny);
    bm_drop(v_miniatura);
    bm_drop(v_kafelek);
    return 0;
}
