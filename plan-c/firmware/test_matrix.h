// test_matrix.h — Arbiter test matrix (30 pairs)
// Auto-generated from test-matrix.md Rev 2.1
// All pairs have geometric mean ≈ 5000 Hz

#ifndef TEST_MATRIX_H
#define TEST_MATRIX_H

#include <Arduino.h>

struct TestPair {
    double f1;           // Hz (higher frequency)
    double f2;           // Hz (lower frequency)
    const char* id;      // "PP1", "CC2", etc.
    uint8_t stratum;     // 0=PP, 1=CC, 2=PC, 3=NC, 4=IR
    char compClass;      // 'A','B','C','D','X' (X=not in primary comparison)
};

// Strata: 0=Prime:Prime, 1=Composite:Composite, 2=Prime:Composite, 3=Non-Coprime, 4=Irrational
static const uint8_t ST_PP = 0;
static const uint8_t ST_CC = 1;
static const uint8_t ST_PC = 2;
static const uint8_t ST_NC = 3;
static const uint8_t ST_IR = 4;

#define NUM_PAIRS 30

static const TestPair testPairs[NUM_PAIRS] = {
    // --- Stratum 1: Prime:Prime coprime (8 pairs) ---
    { 6123.7, 4082.5, "PP1", ST_PP, 'X' },  // 3:2
    { 6454.9, 3872.9, "PP2", ST_PP, 'B' },  // 5:3  — Class B3
    { 5916.1, 4226.5, "PP3", ST_PP, 'B' },  // 7:5  — Class B1
    { 6267.8, 3989.5, "PP4", ST_PP, 'B' },  // 11:7 — Class B2 (crown jewel)
    { 5435.5, 4598.3, "PP5", ST_PP, 'A' },  // 13:11
    { 7637.6, 3273.3, "PP6", ST_PP, 'C' },  // 7:3
    { 7905.7, 3162.3, "PP7", ST_PP, 'C' },  // 5:2
    { 9574.3, 2613.5, "PP8", ST_PP, 'D' },  // 11:3

    // --- Stratum 2: Composite:Composite coprime (9 pairs) ---
    { 5303.3, 4714.0, "CC1", ST_CC, 'A' },  // 9:8
    { 6250.0, 4000.0, "CC2", ST_CC, 'B' },  // 25:16 — Class B2 (crown jewel match)
    { 7500.0, 3333.3, "CC3", ST_CC, 'C' },  // 9:4
    { 6846.5, 3651.5, "CC4", ST_CC, 'X' },  // 15:8
    { 8333.3, 3000.0, "CC5", ST_CC, 'C' },  // 25:9
    { 7000.0, 3571.4, "CC6", ST_CC, 'X' },  // 49:25
    { 6000.0, 4166.7, "CC7", ST_CC, 'B' },  // 36:25 — Class B1 match
    { 6187.2, 4040.6, "CC8", ST_CC, 'X' },  // 49:32
    { 6495.2, 3849.0, "CC9", ST_CC, 'B' },  // 27:16 — Class B3 match

    // --- Stratum 3: Prime:Composite coprime (6 pairs) ---
    { 5590.2, 4472.1, "PC1", ST_PC, 'A' },  // 5:4
    { 5863.1, 4264.0, "PC2", ST_PC, 'X' },  // 11:8
    { 6009.3, 4160.3, "PC3", ST_PC, 'X' },  // 13:9
    { 6614.4, 3779.6, "PC4", ST_PC, 'X' },  // 7:4
    { 8291.6, 3015.1, "PC5", ST_PC, 'C' },  // 11:4
    { 9013.9, 2773.5, "PC6", ST_PC, 'D' },  // 13:4

    // --- Stratum 4: Non-Coprime (3 pairs) ---
    { 7071.1, 3535.5, "NC1", ST_NC, 'X' },  // 4:2 → 2:1
    { 6123.7, 4082.5, "NC2", ST_NC, 'X' },  // 9:6 → 3:2 (must = PP1)
    { 6123.7, 4082.5, "NC3", ST_NC, 'X' },  // 15:10 → 3:2 (must = PP1)

    // --- Stratum 5: Irrational ratios (4 pairs) ---
    { 5946.0, 4204.5, "IR1", ST_IR, 'X' },  // √2:1
    { 6365.7, 3926.5, "IR2", ST_IR, 'B' },  // φ:1   — Class B3 match
    { 5835.8, 4283.5, "IR3", ST_IR, 'A' },  // e/2:1 — Class A match
    { 6268.0, 3989.4, "IR4", ST_IR, 'B' },  // π/2:1 — Class B2 match
};

#endif // TEST_MATRIX_H
