// ============================================================================
// arbiter.ino — Dual-AD9833 DDS controller for Plan C analog experiment
// Teensy 4.1 firmware — Tests prime vs composite frequency ratio interference
// ============================================================================
//
// Hardware:
//   Board A: AD9833 CS=10, 25 MHz oscillator (shared to Board B)
//   Board B: AD9833 CS=9
//   SPI: SCK=13, MOSI=11 (hardware SPI0)
//   Trigger: pin 8 → scope CH4
//   Serial: 115200 baud
//
// Modes:
//   CHAR — Manual serial commands for signal chain characterisation
//   RUN  — Automated randomised test sequence (1200 trials, ~20 min)
//

#include <SPI.h>
#include "test_matrix.h"

// ---- Pin definitions ----
#define CS_A    10
#define CS_B     2
#define TRIGGER  8

// ---- AD9833 constants ----
#define MCLK 25000000.0   // 25 MHz master clock
#define FREQ_MIN 0.1
#define FREQ_MAX 12500000.0

// Control register bits
#define CR_B28    (1 << 13)  // Full 28-bit frequency write
#define CR_RESET  (1 <<  8)  // Reset
#define CR_SLEEP1 (1 <<  5)  // DAC sleep

// ---- Timing (ms) ----
#define SETTLE_MS  500
#define CAPTURE_MS 200
#define GAP_MS     300
#define NUM_BLOCKS   5
#define NUM_PHASES   8

// ---- SPI settings for AD9833: Mode 2, 8 MHz, MSB first ----
static const SPISettings AD9833_SPI(1000000, MSBFIRST, SPI_MODE2);

// ---- State ----
static double freqA = 0.0, freqB = 0.0;
static uint16_t phaseA = 0, phaseB = 0;
static bool running = false;
static bool stopRequested = false;

// ---- Shuffled index array for RUN mode ----
static uint8_t shuffleIdx[NUM_PAIRS];

// ============================================================================
// AD9833 Driver — Bitbang SPI (bypasses hardware SPI peripheral)
// ============================================================================

#define BB_SCK  13
#define BB_MOSI 11

// Set true for verbose SPI bit-level debug (slows down transfers)
static bool spiDebug = false;

void ad9833_write_reg(uint8_t cs_pin, uint16_t data) {
    // Bitbang SPI Mode 2: CPOL=1 (SCK idles HIGH), data sampled on falling edge
    
    if (spiDebug) Serial.printf("  [SPI] CS%d <- 0x%04X  bits:", cs_pin, data);
    
    digitalWrite(cs_pin, LOW);
    delayMicroseconds(10);
    
    for (int i = 15; i >= 0; i--) {
        uint8_t bit = (data >> i) & 1;
        if (spiDebug) Serial.print(bit);
        digitalWrite(BB_MOSI, bit);
        delayMicroseconds(10);
        digitalWrite(BB_SCK, LOW);
        delayMicroseconds(10);
        digitalWrite(BB_SCK, HIGH);
        delayMicroseconds(10);
    }
    
    delayMicroseconds(10);
    digitalWrite(cs_pin, HIGH);
    delayMicroseconds(20);
    if (spiDebug) Serial.println();
}

void ad9833_init(uint8_t cs_pin) {
    pinMode(cs_pin, OUTPUT);
    digitalWrite(cs_pin, HIGH);
    delay(10);

    // Reset: set B28 + RESET (0x2100 — matches proven V5 firmware)
    ad9833_write_reg(cs_pin, 0x2100);
    delay(1);

    // Write FREQ0 = 0 (two 14-bit words with DB15:14 = 01)
    ad9833_write_reg(cs_pin, 0x4000);  // FREQ0 LSB = 0
    ad9833_write_reg(cs_pin, 0x4000);  // FREQ0 MSB = 0

    // Write PHASE0 = 0 (DB15:13 = 110)
    ad9833_write_reg(cs_pin, 0xC000);

    // Clear reset → sine output active (0x2000)
    ad9833_write_reg(cs_pin, 0x2000);
    delay(1);
    
    Serial.printf("[DDS] Init CS=%d complete\n", cs_pin);
}

bool ad9833_set_freq(uint8_t cs_pin, double freq_hz) {
    if (freq_hz < FREQ_MIN || freq_hz > FREQ_MAX) {
        Serial.printf("ERR: freq %.2f out of range [%.1f, %.1f]\n", freq_hz, FREQ_MIN, FREQ_MAX);
        return false;
    }

    // 28-bit frequency word: freqWord = freq * 2^28 / MCLK
    uint32_t freqWord = (uint32_t)((freq_hz * 268435456.0) / MCLK + 0.5);

    uint16_t lsb = (freqWord & 0x3FFF) | 0x4000;        // DB15:14=01, low 14 bits
    uint16_t msb = ((freqWord >> 14) & 0x3FFF) | 0x4000; // DB15:14=01, high 14 bits

    Serial.printf("[DDS] CS=%d freq=%.2f freqWord=%lu lsb=0x%04X msb=0x%04X\n", 
                  cs_pin, freq_hz, freqWord, lsb, msb);

    // Match proven V5 sequence: control word with B28+RESET, freq words, then exit reset
    ad9833_write_reg(cs_pin, 0x2100);  // B28 + RESET
    ad9833_write_reg(cs_pin, lsb);
    ad9833_write_reg(cs_pin, msb);
    ad9833_write_reg(cs_pin, 0x2000);  // Exit reset, sine
    return true;
}

void ad9833_set_phase(uint8_t cs_pin, uint16_t phase_12bit) {
    phase_12bit &= 0x0FFF;  // Mask to 12 bits
    // PHASE0: DB15:13 = 110, DB12 = 0, DB11:0 = phase
    ad9833_write_reg(cs_pin, 0xC000 | phase_12bit);
}

void ad9833_sleep(uint8_t cs_pin) {
    ad9833_write_reg(cs_pin, CR_B28 | CR_RESET | CR_SLEEP1);
}

void ad9833_wake(uint8_t cs_pin) {
    ad9833_write_reg(cs_pin, CR_B28);  // Clear reset and sleep → sine
}

// ============================================================================
// Helpers
// ============================================================================

uint16_t deg_to_phase12(double deg) {
    // 0°-360° → 0-4095
    while (deg < 0.0) deg += 360.0;
    while (deg >= 360.0) deg -= 360.0;
    return (uint16_t)((deg / 360.0) * 4096.0) & 0x0FFF;
}

void print_status() {
    Serial.println("=== ARBITER STATUS ===");
    Serial.printf("  DDS A: %.2f Hz, phase %u (%.1f°)\n", freqA, phaseA, phaseA * 360.0 / 4096.0);
    Serial.printf("  DDS B: %.2f Hz, phase %u (%.1f°)\n", freqB, phaseB, phaseB * 360.0 / 4096.0);
    Serial.printf("  Mode: %s\n", running ? "RUN" : "CHAR");
    Serial.printf("  Pins: CS_A=%d CS_B=%d TRIGGER=%d\n", CS_A, CS_B, TRIGGER);
    Serial.printf("  MCLK: %.0f Hz\n", MCLK);
}

void print_help() {
    Serial.println(F(
        "=== ARBITER COMMANDS ===\n"
        "  FA <freq>          Set DDS A frequency (Hz)\n"
        "  FB <freq>          Set DDS B frequency (Hz)\n"
        "  PA <deg>           Set DDS A phase (0-360)\n"
        "  PB <deg>           Set DDS B phase (0-360)\n"
        "  OFF A|B|BOTH       Turn off DDS output(s)\n"
        "  ON A|B|BOTH        Turn on DDS output(s)\n"
        "  SWEEP A|B <start> <stop> <step> <dwell_ms>\n"
        "  IM3 <f1> <f2>      Set both DDS for IM3 test\n"
        "  STATUS             Print current state\n"
        "  RUN                Start automated test sequence\n"
        "  STOP               Abort test sequence\n"
        "  HELP               This message\n"
    ));
}

// ============================================================================
// Fisher-Yates shuffle seeded from analog noise
// ============================================================================

void seed_from_noise() {
    uint32_t seed = 0;
    for (int i = 0; i < 32; i++) {
        seed = (seed << 1) | (analogRead(A0) & 1);
        delayMicroseconds(50);
    }
    randomSeed(seed);
}

void shuffle_pairs() {
    for (uint8_t i = 0; i < NUM_PAIRS; i++) shuffleIdx[i] = i;
    for (uint8_t i = NUM_PAIRS - 1; i > 0; i--) {
        uint8_t j = random(0, i + 1);
        uint8_t tmp = shuffleIdx[i];
        shuffleIdx[i] = shuffleIdx[j];
        shuffleIdx[j] = tmp;
    }
}

// ============================================================================
// RUN mode — Automated test sequence
// ============================================================================

void run_sequence() {
    running = true;
    stopRequested = false;

    Serial.println("RUN_START");
    Serial.println("# block, pair_id, stratum, compClass, f1, f2, phase_step, millis");

    seed_from_noise();

    for (int block = 1; block <= NUM_BLOCKS && !stopRequested; block++) {
        shuffle_pairs();

        for (int p = 0; p < NUM_PAIRS && !stopRequested; p++) {
            const TestPair& pair = testPairs[shuffleIdx[p]];

            for (int ps = 0; ps < NUM_PHASES && !stopRequested; ps++) {
                uint16_t phase_b = ps * 512;  // 8 steps × 512 = 4096 (full circle)

                // Set frequencies and phases
                ad9833_set_freq(CS_A, pair.f1);
                ad9833_set_phase(CS_A, 0);
                ad9833_set_freq(CS_B, pair.f2);
                ad9833_set_phase(CS_B, phase_b);

                // Settle
                delay(SETTLE_MS);

                // Trigger HIGH — scope captures
                digitalWriteFast(TRIGGER, HIGH);
                delay(CAPTURE_MS);
                digitalWriteFast(TRIGGER, LOW);

                // Print CSV line
                Serial.printf("%d,%s,%u,%c,%.1f,%.1f,%d,%lu\n",
                    block, pair.id, pair.stratum, pair.compClass,
                    pair.f1, pair.f2, ps, millis());

                // Inter-trial gap
                delay(GAP_MS);

                // Check for STOP command
                if (Serial.available()) {
                    String cmd = Serial.readStringUntil('\n');
                    cmd.trim();
                    cmd.toUpperCase();
                    if (cmd == "STOP") {
                        stopRequested = true;
                        Serial.println("RUN_ABORTED");
                    }
                }
            }
        }
        if (!stopRequested) {
            Serial.printf("BLOCK_DONE %d\n", block);
        }
    }

    if (!stopRequested) {
        Serial.println("RUN_COMPLETE");
    }

    running = false;
}

// ============================================================================
// Command parser
// ============================================================================

void process_command(String& cmd) {
    cmd.trim();
    if (cmd.length() == 0) return;

    // Uppercase copy for matching (keep original for numeric parsing)
    String upper = cmd;
    upper.toUpperCase();

    // --- FA / FB ---
    if (upper.startsWith("FA ")) {
        double f = cmd.substring(3).toFloat();
        if (ad9833_set_freq(CS_A, f)) {
            freqA = f;
            Serial.printf("OK FA=%.2f Hz\n", freqA);
        }
    }
    else if (upper.startsWith("FB ")) {
        double f = cmd.substring(3).toFloat();
        if (ad9833_set_freq(CS_B, f)) {
            freqB = f;
            Serial.printf("OK FB=%.2f Hz\n", freqB);
        }
    }
    // --- PA / PB ---
    else if (upper.startsWith("PA ")) {
        double deg = cmd.substring(3).toFloat();
        phaseA = deg_to_phase12(deg);
        ad9833_set_phase(CS_A, phaseA);
        Serial.printf("OK PA=%.1f° (reg=%u)\n", deg, phaseA);
    }
    else if (upper.startsWith("PB ")) {
        double deg = cmd.substring(3).toFloat();
        phaseB = deg_to_phase12(deg);
        ad9833_set_phase(CS_B, phaseB);
        Serial.printf("OK PB=%.1f° (reg=%u)\n", deg, phaseB);
    }
    // --- OFF ---
    else if (upper.startsWith("OFF")) {
        String arg = upper.substring(4);
        arg.trim();
        if (arg == "A" || arg == "BOTH") ad9833_sleep(CS_A);
        if (arg == "B" || arg == "BOTH") ad9833_sleep(CS_B);
        Serial.printf("OK OFF %s\n", arg.c_str());
    }
    // --- ON ---
    else if (upper.startsWith("ON")) {
        String arg = upper.substring(3);
        arg.trim();
        if (arg == "A" || arg == "BOTH") ad9833_wake(CS_A);
        if (arg == "B" || arg == "BOTH") ad9833_wake(CS_B);
        Serial.printf("OK ON %s\n", arg.c_str());
    }
    // --- SWEEP ---
    else if (upper.startsWith("SWEEP")) {
        // SWEEP A|B <start> <stop> <step> <dwell_ms>
        char which;
        double start, stop, step;
        unsigned long dwell;
        if (sscanf(cmd.c_str() + 6, "%c %lf %lf %lf %lu", &which, &start, &stop, &step, &dwell) == 5) {
            which = toupper(which);
            uint8_t cs = (which == 'A') ? CS_A : CS_B;
            Serial.printf("SWEEP %c: %.1f → %.1f step %.1f dwell %lu ms\n", which, start, stop, step, dwell);
            for (double f = start; (step > 0 ? f <= stop : f >= stop); f += step) {
                ad9833_set_freq(cs, f);
                Serial.printf("  %.1f Hz\n", f);
                delay(dwell);
                if (Serial.available()) {
                    String s = Serial.readStringUntil('\n');
                    s.trim();
                    s.toUpperCase();
                    if (s == "STOP") { Serial.println("SWEEP_ABORTED"); return; }
                }
            }
            Serial.println("SWEEP_DONE");
        } else {
            Serial.println("ERR: SWEEP A|B <start> <stop> <step> <dwell_ms>");
        }
    }
    // --- IM3 ---
    else if (upper.startsWith("IM3")) {
        double f1, f2;
        if (sscanf(cmd.c_str() + 4, "%lf %lf", &f1, &f2) == 2) {
            if (ad9833_set_freq(CS_A, f1) && ad9833_set_freq(CS_B, f2)) {
                freqA = f1;
                freqB = f2;
                Serial.printf("OK IM3: A=%.1f B=%.1f  IM3L=%.1f IM3H=%.1f\n",
                    f1, f2, 2*f1 - f2, 2*f2 - f1);
            }
        } else {
            Serial.println("ERR: IM3 <f1> <f2>");
        }
    }
    // --- STATUS ---
    else if (upper == "STATUS") {
        print_status();
    }
    // --- RUN ---
    else if (upper == "RUN") {
        if (running) {
            Serial.println("ERR: already running");
        } else {
            run_sequence();
        }
    }
    // --- STOP ---
    else if (upper == "STOP") {
        if (running) {
            stopRequested = true;
        } else {
            Serial.println("OK (not running)");
        }
    }
    // --- HELP ---
    else if (upper == "HELP") {
        print_help();
    }
    // --- DEBUG ---
    else if (upper == "DEBUG") {
        spiDebug = !spiDebug;
        Serial.printf("OK SPI debug %s\n", spiDebug ? "ON" : "OFF");
    }
    else {
        Serial.printf("ERR: unknown command '%s' — type HELP\n", cmd.c_str());
    }
}

// ============================================================================
// Setup & Loop
// ============================================================================

void setup() {
    Serial.begin(115200);
    while (!Serial && millis() < 3000) {}  // Wait up to 3s for USB serial

    // Trigger pin
    pinMode(TRIGGER, OUTPUT);
    digitalWriteFast(TRIGGER, LOW);

    // Bitbang SPI pins
    pinMode(BB_SCK, OUTPUT);
    pinMode(BB_MOSI, OUTPUT);
    digitalWrite(BB_SCK, HIGH);   // CPOL=1: idle HIGH
    digitalWrite(BB_MOSI, LOW);
    
    // Quick pin test — pulse SCK so we can see it on scope
    Serial.println("[SPI] Pin 13 test pulse...");
    for (int i = 0; i < 10; i++) {
        digitalWrite(BB_SCK, LOW);
        delayMicroseconds(100);
        digitalWrite(BB_SCK, HIGH);
        delayMicroseconds(100);
    }
    Serial.println("[SPI] Pulse done — check scope on pin 13");

    // Test CS_B pin — 10 pulses so we can verify it toggles
    pinMode(CS_B, OUTPUT);
    digitalWrite(CS_B, HIGH);
    Serial.printf("[SPI] CS_B pin %d test pulse...\n", CS_B);
    for (int i = 0; i < 10; i++) {
        digitalWrite(CS_B, LOW);
        delayMicroseconds(500);
        digitalWrite(CS_B, HIGH);
        delayMicroseconds(500);
    }
    Serial.printf("[SPI] CS_B pin %d pulse done\n", CS_B);

    // Initialise both AD9833s
    ad9833_init(CS_A);
    ad9833_init(CS_B);

    Serial.println(F(
        "\n"
        "╔═══════════════════════════════════╗\n"
        "║   ARBITER v1.0 — Dual AD9833 DDS  ║\n"
        "║   Plan C Analog Experiment         ║\n"
        "║   Teensy 4.1 | 25 MHz MCLK         ║\n"
        "╚═══════════════════════════════════╝\n"
    ));
    Serial.println("Ready. Type HELP for commands.");
}

void loop() {
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        process_command(cmd);
    }
}
